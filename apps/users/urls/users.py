
from django.urls import path
from apps.users.views import (
    UserProfileView, UserProfileDetailView,
    LoginHistoryView, ActiveSessionsView,
)

urlpatterns = [
    # Profile Management
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/detail/', UserProfileDetailView.as_view(), name='user-profile-detail'),

    # Security
    path('login-history/', LoginHistoryView.as_view(), name='user-login-history'),
    path('sessions/', ActiveSessionsView.as_view(), name='user-sessions'),
    path('sessions/<str:session_id>/', ActiveSessionsView.as_view(), name='user-session-terminate'),
]