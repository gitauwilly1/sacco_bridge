
from django.urls import path
from apps.users.views import (
    AccountDeletionView, AccountDeactivationView, ActiveSessionsView, AdminUserManagementView, AuditLogView, DataExportView, ProfilePictureUploadView, UserProfileView, UserProfileDetailView,
    LoginHistoryView,PhoneNumberUpdateView,
)

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/detail/', UserProfileDetailView.as_view(), name='user-profile-detail'),
    path('login-history/', LoginHistoryView.as_view(), name='user-login-history'),
    path('admin/manage/', AdminUserManagementView.as_view(), name='admin-user-manage'),
    path('phone-number/', PhoneNumberUpdateView.as_view(), name='phone-number-update'),
    path('profile/picture/', ProfilePictureUploadView.as_view(), name='user-profile-picture'),
    path('sessions/', ActiveSessionsView.as_view(), name='user-sessions'),
    path('sessions/<uuid:session_id>/', ActiveSessionsView.as_view(), name='user-session-terminate'),
    path('delete-account/', AccountDeletionView.as_view(), name='user-delete-account'),
    path('export-data/', DataExportView.as_view(), name='user-export-data'),  
    path('deactivate/', AccountDeactivationView.as_view(), name='user-deactivate'),
    path('admin/audit/', AuditLogView.as_view(), name='admin-audit-log'),
]