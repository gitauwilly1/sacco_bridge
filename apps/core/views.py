"""Core utility views."""

from django.core.cache import cache
from django.db import connections
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    health_status = {
        'status': 'healthy',
        'database': 'up',
        'cache': 'up',
        'timestamp': str(timezone.now()),
        'version': '1.0.0',
    }

    # Check database
    try:
        connections['default'].cursor()
        connections['default'].ensure_connection()
    except Exception:
        health_status['database'] = 'down'
        health_status['status'] = 'unhealthy'

    # Check cache
    try:
        test_key = 'health_check_test'
        cache.set(test_key, 'ok', 10)
        if cache.get(test_key) != 'ok':
            raise Exception('Cache write/read mismatch')
        cache.delete(test_key)
    except Exception:
        health_status['cache'] = 'down'
        health_status['status'] = 'unhealthy'

    status_code = 200 if health_status['status'] == 'healthy' else 503
    return Response(health_status, status=status_code)


@api_view(['POST'])
@permission_classes([AllowAny])
def client_error_log(request):
    from .models import ClientErrorLog

    errors = request.data.get('errors', [])
    if not isinstance(errors, list):
        errors = [request.data]

    user = request.user if request.user.is_authenticated else None

    for entry in errors:
        ClientErrorLog.objects.create(
            level=entry.get('level', 'ERROR'),
            message=entry.get('message', ''),
            url=entry.get('url', ''),
            user_agent=entry.get('user_agent', ''),
            stack=entry.get('stack', ''),
            extra_data={k: v for k, v in entry.items() if k not in ('level', 'message', 'url', 'user_agent', 'stack', 'timestamp')},
            user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

    return Response({'status': 'logged'}, status=201)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def admin_approval_list(request):
    from .models import AdminApproval
    from .serializers import AdminApprovalSerializer

    if request.method == 'GET':
        user = request.user if request.user.is_authenticated else None
        if not user or not user.is_staff:
            return Response({'error': 'Permission denied'}, status=403)
        status_filter = request.query_params.get('status', 'PENDING')
        qs = AdminApproval.objects.filter(status=status_filter).select_related(
            'requested_by', 'reviewed_by',
        )
        page = int(request.query_params.get('page', 1))
        page_size = 20
        total = qs.count()
        results = qs[(page - 1) * page_size:page * page_size]
        return Response({
            'results': AdminApprovalSerializer(results, many=True).data,
            'count': total,
        })

    # POST — create a new approval request
    user = request.user if request.user.is_authenticated else None
    if not user or not user.is_staff:
        return Response({'error': 'Permission denied'}, status=403)
    serializer = AdminApprovalSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save(requested_by=user)
    return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_approval_review(request, pk):
    from .models import AdminApproval

    user = request.user if request.user.is_authenticated else None
    if not user or not user.is_staff:
        return Response({'error': 'Permission denied'}, status=403)

    try:
        approval = AdminApproval.objects.get(id=pk, status='PENDING')
    except AdminApproval.DoesNotExist:
        return Response({'error': 'Approval request not found or already reviewed'}, status=404)

    if approval.requested_by == user:
        return Response({'error': 'Cannot review your own request'}, status=400)

    action = request.data.get('action')
    notes = request.data.get('notes', '')

    if action == 'approve':
        approval.approve(user, notes)
    elif action == 'reject':
        approval.reject(user, notes)
    else:
        return Response({'error': 'Invalid action. Use "approve" or "reject".'}, status=400)

    return Response({'status': 'ok', 'new_status': approval.status})