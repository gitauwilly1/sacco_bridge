from django.urls import path
from apps.users.views import (
    RegistrationView, LoginView, TwoFactorSetupView,
    EmailVerificationView, PhoneVerificationView,
    ResendVerificationView, GoogleAuthView,
    TokenRefreshViewCustom, LogoutView,
    PasswordChangeView, PasswordResetRequestView,
    PasswordResetConfirmView
)

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('token/refresh/', TokenRefreshViewCustom.as_view(), name='auth-token-refresh'),
    path('google/', GoogleAuthView.as_view(), name='auth-google'),
    path('2fa/setup/', TwoFactorSetupView.as_view(), name='auth-2fa-setup'),
    path('verify/email/', EmailVerificationView.as_view(), name='auth-verify-email'),
    path('verify/phone/', PhoneVerificationView.as_view(), name='auth-verify-phone'),
    path('verify/resend/', ResendVerificationView.as_view(), name='auth-verify-resend'),
    path('password/change/', PasswordChangeView.as_view(), name='auth-password-change'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
]