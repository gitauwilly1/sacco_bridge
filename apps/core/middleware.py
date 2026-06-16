import uuid
import time
import logging
from django.conf import settings
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.start_time = time.time()
        request.request_id = str(uuid.uuid4())

        self.log_request(request)
        response = self.get_response(request)
        self.log_response(request, response)

        response['X-Request-ID'] = request.request_id
        response['X-Response-Time'] = f"{self.calculate_request_time(request):.3f}s"

        return response

    def log_request(self, request):
        logger.info(
            f"Request started: {request.method} {request.get_full_path()}",
            extra={
                'request_id': request.request_id,
                'method': request.method,
                'path': request.get_full_path(),
                'remote_addr': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'user_id': request.user.id if request.user.is_authenticated else None,
            }
        )

    def log_response(self, request, response):
        duration = self.calculate_request_time(request)
        logger.info(
            f"Request completed: {request.method} {request.get_full_path()} - {response.status_code} ({duration:.3f}s)",
            extra={
                'request_id': request.request_id,
                'status_code': response.status_code,
                'duration': duration,
            }
        )

    def calculate_request_time(self, request):
        return time.time() - request.start_time

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class APIVersionMiddleware:

    SUPPORTED_VERSIONS = ['v1']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        api_version = request.headers.get('X-API-Version', 'v1')

        if api_version not in self.SUPPORTED_VERSIONS:
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'unsupported_api_version',
                    'message': f'API version {api_version} is not supported.'
                }
            }, status=400)

        request.api_version = api_version
        response = self.get_response(request)
        response['X-API-Version'] = api_version
        return response


class SecurityHeadersMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        return response
    

@database_sync_to_async
def get_user_from_token(token):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.tokens import AccessToken
    from rest_framework_simplejwt.exceptions import TokenError

    User = get_user_model()

    try:
        access_token = AccessToken(token)
        user_id = access_token.get('user_id')
        if user_id:
            return User.objects.get(id=user_id, is_active=True)
    except (TokenError, User.DoesNotExist, Exception):
        pass

    return AnonymousUser()
class WebSocketAuthMiddleware:

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from urllib.parse import parse_qs
        from django.contrib.auth.models import AnonymousUser
        
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)


class IdempotencyMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check mutation methods
        if request.method in ('POST', 'PATCH', 'PUT', 'DELETE'):
            idempotency_key = request.headers.get('X-Idempotency-Key')

            if idempotency_key:
                cache_key = f'idempotency:{idempotency_key}'
                from django.core.cache import cache

                # Check if we've seen this key before
                cached_response = cache.get(cache_key)
                if cached_response is not None:
                    from django.http import JsonResponse
                    return JsonResponse(
                        cached_response,
                        status=cached_response.get('status', 200),
                    )

                response = self.get_response(request)

                # Cache successful responses for 24 hours
                if 200 <= response.status_code < 500:
                    try:
                        import json
                        response_data = json.loads(response.content)
                        response_data['_idempotent'] = True
                        cache.set(cache_key, response_data, 86400)  # 24 hours
                    except Exception:
                        pass

                return response

        return self.get_response(request)

class RequestTimeoutMiddleware:

    SENSITIVE_PATHS = [
        '/api/v1/transactions/settlements/',
        '/api/v1/payments/mpesa/stk-push/',
        '/api/v1/chamas/loans/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import signal

        path = request.path

        is_sensitive = any(path.startswith(p) for p in self.SENSITIVE_PATHS)

        if is_sensitive and request.method in ('POST', 'PATCH', 'PUT'):
            def timeout_handler(signum, frame):
                raise TimeoutError('Request timed out')

            try:
                import signal
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(60)  # 60 second timeout
                response = self.get_response(request)
                signal.alarm(0)
                return response
            except TimeoutError:
                from django.http import JsonResponse
                return JsonResponse(
                    {
                        'success': False,
                        'error': {
                            'code': 'request_timeout',
                            'message': 'Request timed out. Please try again.',
                        }
                    },
                    status=408,
                )
            except Exception:
                signal.alarm(0)
                raise

        return self.get_response(request)