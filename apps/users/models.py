import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from apps.core.models import BaseModel, AddressMixin


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set.'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('phone_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email=email)


class Role(models.TextChoices):
    PLATFORM_ADMIN = 'PLATFORM_ADMIN', _('Platform Administrator')
    SACCO_ADMIN = 'SACCO_ADMIN', _('SACCO Administrator')
    INVESTOR = 'INVESTOR', _('Investor')
    SELLER = 'SELLER', _('Seller')
    INSTITUTIONAL_BUYER = 'INSTITUTIONAL_BUYER', _('Institutional Buyer')
    SUPPORT_AGENT = 'SUPPORT_AGENT', _('Support Agent')


class IDVerificationStatus(models.TextChoices):
    UNVERIFIED = 'UNVERIFIED', _('Unverified')
    PENDING = 'PENDING', _('Pending Verification')
    VERIFIED = 'VERIFIED', _('Verified')
    REJECTED = 'REJECTED', _('Rejected')
    EXPIRED = 'EXPIRED', _('Expired')


class User(AbstractBaseUser, PermissionsMixin):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    phone_number = models.CharField(
        max_length=20, null=True, blank=True, unique=True, db_index=True,
        validators=[RegexValidator(regex=r'^(?:\+?254|0)?[17]\d{8}$', message=_('Enter a valid Kenyan phone number.'))]
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    national_id = models.CharField(max_length=20, blank=True, default='')
    id_verification_status = models.CharField(
        max_length=20, choices=IDVerificationStatus.choices, default=IDVerificationStatus.UNVERIFIED
    )
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True, default='')
    email_verification_expiry = models.DateTimeField(null=True, blank=True)
    phone_verification_code = models.CharField(max_length=6, blank=True, default='')
    phone_verification_expiry = models.DateTimeField(null=True, blank=True)
    email_verification_code = models.CharField(max_length=6, blank=True, default='')
    email_verification_expiry = models.DateTimeField(null=True, blank=True)
    email_verification_attempts = models.PositiveIntegerField(default=0)
    email_last_verification_sent = models.DateTimeField(null=True, blank=True)
    
    phone_verification_code = models.CharField(max_length=6, blank=True, default='')
    phone_verification_expiry = models.DateTimeField(null=True, blank=True)
    phone_verification_attempts = models.PositiveIntegerField(default=0)
    phone_last_verification_sent = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pictures/%Y/%m/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_device = models.CharField(max_length=255, blank=True, default='')
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    totp_secret = models.CharField(max_length=255, blank=True, default='')
    two_factor_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(
        default=list,
        help_text=_("Hashed backup codes for 2FA recovery.")
    )
    preferred_language = models.CharField(max_length=10, default='en', choices=[('en', 'English'), ('sw', 'Kiswahili')])

    # Renamed from notification_preferences to notification_settings
    # to avoid conflict with NotificationPreference reverse relation
    notification_settings = models.JSONField(
        default=dict,
        help_text=_("User's notification channel preferences as a JSON object.")
    )

    trust_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    # Transaction limits
    daily_transaction_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=50000.00,
        help_text=_("Maximum daily transaction amount.")
    )
    monthly_transaction_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=200000.00,
        help_text=_("Maximum monthly transaction amount.")
    )
    per_transaction_limit = models.DecimalField(
        max_digits=15, decimal_places=2, default=25000.00,
        help_text=_("Maximum single transaction amount.")
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['id_verification_status']),
            models.Index(fields=['date_joined']),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    def get_initials(self):
        first = self.first_name[0].upper() if self.first_name else ''
        last = self.last_name[0].upper() if self.last_name else ''
        return f"{first}{last}"

    def has_role(self, role):
        return self.user_roles.filter(role=role, is_active=True).exists()

    def add_role(self, role, assigned_by=None):
        return UserRole.objects.get_or_create(user=self, role=role, defaults={'assigned_by': assigned_by})

    def remove_role(self, role):
        UserRole.objects.filter(user=self, role=role).update(is_active=False)

    def is_account_locked(self):
        if self.account_locked_until and self.account_locked_until > timezone.now():
            return True
        return False

    def increment_failed_login(self):
        from django.conf import settings
        max_attempts = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        cooloff = getattr(settings, 'AXES_COOLOFF_TIME', 30)

        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.account_locked_until = timezone.now() + timezone.timedelta(minutes=cooloff)
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])

    def reset_failed_login(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])


class UserRole(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.CharField(max_length=30, choices=Role.choices)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='roles_assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('User Role')
        verbose_name_plural = _('User Roles')
        unique_together = ['user', 'role']
        indexes = [models.Index(fields=['user', 'role']), models.Index(fields=['role'])]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"


class UserProfile(BaseModel, AddressMixin):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    occupation = models.CharField(max_length=255, blank=True, default='')
    employer = models.CharField(max_length=255, blank=True, default='')
    monthly_income_range = models.CharField(max_length=50, blank=True, default='')
    source_of_funds = models.CharField(max_length=255, blank=True, default='')
    risk_tolerance = models.CharField(
        max_length=20,
        choices=[('CONSERVATIVE', 'Conservative'), ('MODERATE', 'Moderate'), ('AGGRESSIVE', 'Aggressive')],
        default='MODERATE'
    )
    investment_experience = models.CharField(
        max_length=20,
        choices=[('NONE', 'No Experience'), ('BEGINNER', 'Beginner'), ('INTERMEDIATE', 'Intermediate'), ('EXPERT', 'Expert')],
        default='BEGINNER'
    )

    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')

    def __str__(self):
        return f"Profile: {self.user.get_full_name()}"


class LoginHistory(models.Model):

    uuid = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True,
        help_text=_("Public session identifier.")
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    login_timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default='')
    device_type = models.CharField(max_length=50, blank=True, default='')
    login_successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True, default='')
    location_city = models.CharField(max_length=100, blank=True, default='')
    
    class Meta:
        verbose_name = _('Login History')
        verbose_name_plural = _('Login Histories')
        ordering = ['-login_timestamp']

    def __str__(self):
        status = "Success" if self.login_successful else "Failed"
        return f"{self.user.email} - {status} at {self.login_timestamp}"