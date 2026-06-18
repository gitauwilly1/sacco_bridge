from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from apps.core.views import health_check
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    path('health/', health_check, name='health-check'),

    # API Schema and Documentation
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/v1/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
    path(
        'api/v1/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),

    # API Endpoints
    path('api/v1/auth/', include('apps.users.urls.auth')),
    path('api/v1/users/', include('apps.users.urls.users')),
    path('api/v1/chamas/', include('apps.chamas.urls')),
    path('api/v1/investments/', include('apps.investments.urls')),
    path('api/v1/dashboard/', include('apps.users.urls.dashboard')),
    path('api/v1/transactions/', include('apps.transactions.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/chatbot/', include('apps.chatbot.urls')),
    path('api/v1/payments/mpesa/', include('apps.mpesa.urls')),
    path('api/v1/receipts/', include('apps.receipts.urls')),
    path('api/v1/legal/', include('apps.legal.urls')),
    path('api/v1/reports/', include('apps.reports.urls')),
    path('api/v1/activity/', include('apps.activity.urls')),
    path('api/v1/webhooks/', include('apps.webhooks.urls')),
    path('api/v1/scoring/', include('apps.scoring.urls')),
    path('api/v1/escrow/', include('apps.escrow.urls')),
    path('api/v1/fraud/', include('apps.fraud.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin site configuration
admin.site.site_header = 'Sacco Bridge Administration'
admin.site.site_title = 'Sacco Bridge Admin'
admin.site.index_title = 'Platform Management'