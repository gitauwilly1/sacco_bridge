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
    errors = request.data.get('errors', [])
    if not isinstance(errors, list):
        errors = [request.data]
    import logging
    logger = logging.getLogger('sacco_bridge.client_errors')
    for entry in errors:
        logger.warning('Client error: %s | URL: %s | Level: %s',
                       entry.get('message', ''), entry.get('url', ''), entry.get('level', 'ERROR'))
    return Response({'success': True, 'data': {}})
