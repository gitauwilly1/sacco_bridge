from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from apps.users.models import User, UserRole, UserProfile, LoginHistory


class UserRoleInline(admin.TabularInline):
    model = UserRole
    fk_name = 'user'
    extra = 0
    fields = ('role', 'assigned_by', 'is_active', 'expires_at', 'assigned_at')
    readonly_fields = ('assigned_at',)
    autocomplete_fields = ('assigned_by',)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = _('Profile')
    fk_name = 'user'


class LoginHistoryInline(admin.TabularInline):
    model = LoginHistory
    extra = 0
    fields = ('login_timestamp', 'ip_address', 'device_type', 'login_successful')
    readonly_fields = fields
    can_delete = False
    max_num = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'phone_number', 'get_full_name', 'is_active',
        'is_staff', 'id_verification_status', 'trust_score', 'date_joined'
    ]
    list_filter = [
        'is_active', 'is_staff', 'id_verification_status',
        'email_verified', 'phone_verified', 'two_factor_enabled', 'date_joined'
    ]
    search_fields = ['email', 'phone_number', 'first_name', 'last_name', 'national_id']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'phone_number', 'password')}),
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name', 'national_id', 'date_of_birth', 'profile_picture')
        }),
        (_('Verification Status'), {
            'fields': ('id_verification_status', 'email_verified', 'phone_verified')
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Security'), {
            'fields': ('two_factor_enabled', 'failed_login_attempts', 'account_locked_until')
        }),
        (_('Preferences'), {
            'fields': ('preferred_language', 'notification_settings')
        }),
        (_('Trust & Reputation'), {
            'fields': ('trust_score',)
        }),
        (_('Important Dates'), {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'phone_number', 'first_name', 'last_name',
                'password1', 'password2', 'is_staff', 'is_superuser',
            ),
        }),
    )

    inlines = [UserRoleInline, UserProfileInline, LoginHistoryInline]
    readonly_fields = ('last_login', 'date_joined', 'trust_score')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_active', 'assigned_at', 'expires_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    autocomplete_fields = ('user', 'assigned_by')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'occupation', 'risk_tolerance', 'investment_experience')
    search_fields = ('user__email',)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_timestamp', 'ip_address', 'device_type', 'login_successful')
    list_filter = ('login_successful', 'device_type', 'login_timestamp')
    search_fields = ('user__email', 'ip_address')
    readonly_fields = [field.name for field in LoginHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False