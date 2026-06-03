
from django.urls import path
from apps.users.views import (
    AdminUserManagementView, UserProfileView, UserProfileDetailView,
    LoginHistoryView,PhoneNumberUpdateView,
)

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/detail/', UserProfileDetailView.as_view(), name='user-profile-detail'),
    path('login-history/', LoginHistoryView.as_view(), name='user-login-history'),
    path('admin/manage/', AdminUserManagementView.as_view(), name='admin-user-manage'),
    path('phone-number/', PhoneNumberUpdateView.as_view(), name='phone-number-update'),
]