from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

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
    path('api/v1/transactions/', include('apps.transactions.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin site configuration
admin.site.site_header = 'Sacco Bridge Administration'
admin.site.site_title = 'Sacco Bridge Admin'
admin.site.index_title = 'Platform Management'