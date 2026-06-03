
from django.urls import path
from apps.users.views import (
    UserProfileView, UserProfileDetailView,
    LoginHistoryView,
)

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/detail/', UserProfileDetailView.as_view(), name='user-profile-detail'),
    path('login-history/', LoginHistoryView.as_view(), name='user-login-history'),
]