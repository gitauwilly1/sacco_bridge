from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.activity.models import ActivityLog, ActivityType
from apps.activity.serializers import ActivityLogSerializer
from apps.core.pagination import SmallPagination


class UserActivityFeedView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Activity'],
        summary='Get user activity feed',
        description='Returns paginated activity feed for the authenticated user.',
        parameters=[
            OpenApiParameter(name='type', description='Filter by activity type', required=False, type=str),
            OpenApiParameter(name='chama_id', description='Filter by chama', required=False, type=str),
            OpenApiParameter(name='days', description='Last N days (default 30)', required=False, type=int),
        ]
    )
    def get(self, request):
        activities = ActivityLog.objects.filter(user=request.user)

        # Filter by activity type
        activity_type = request.query_params.get('type')
        if activity_type and activity_type in dict(ActivityType.choices):
            activities = activities.filter(activity_type=activity_type)

        # Filter by chama
        chama_id = request.query_params.get('chama_id')
        if chama_id:
            activities = activities.filter(chama_id=chama_id)

        # Filter by date range
        days = int(request.query_params.get('days', 30))
        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(days=days)
        activities = activities.filter(created_at__gte=cutoff)

        activities = activities.select_related('user', 'chama', 'sacco')
        activities = activities.order_by('-created_at')

        paginator = SmallPagination()
        page = paginator.paginate_queryset(activities, request)
        serializer = ActivityLogSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)


class ChamaActivityFeedView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Activity'],
        summary='Get chama activity feed',
        description='Returns paginated activity feed for a specific chama.',
        parameters=[
            OpenApiParameter(name='type', description='Filter by activity type', required=False, type=str),
            OpenApiParameter(name='days', description='Last N days (default 30)', required=False, type=int),
        ]
    )
    def get(self, request, chama_id):
        # Verify user is a member
        from apps.chamas.models import ChamaMember
        is_member = ChamaMember.objects.filter(
            chama_id=chama_id,
            user=request.user,
            is_active=True,
        ).exists()

        if not is_member:
            return Response({
                'success': False,
                'error': {
                    'code': 'not_member',
                    'message': 'You are not a member of this chama.'
                }
            }, status=403)

        activities = ActivityLog.objects.filter(chama_id=chama_id)

        activity_type = request.query_params.get('type')
        if activity_type and activity_type in dict(ActivityType.choices):
            activities = activities.filter(activity_type=activity_type)

        days = int(request.query_params.get('days', 30))
        from django.utils import timezone
        cutoff = timezone.now() - timezone.timedelta(days=days)
        activities = activities.filter(created_at__gte=cutoff)

        activities = activities.select_related('user', 'chama', 'sacco')
        activities = activities.order_by('-created_at')

        paginator = SmallPagination()
        page = paginator.paginate_queryset(activities, request)
        serializer = ActivityLogSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)