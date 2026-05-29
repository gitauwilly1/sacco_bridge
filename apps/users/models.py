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
    CHAMA_TREASURER = 'CHAMA_TREASURER', _('Chama Treasurer')
    CHAMA_CHAIRPERSON = 'CHAMA_CHAIRPERSON', _('Chama Chairperson')
    CHAMA_SECRETARY = 'CHAMA_SECRETARY', _('Chama Secretary')
    CHAMA_MEMBER = 'CHAMA_MEMBER', _('Chama Member')
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

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for the user.")
    )

    email = models.EmailField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("Email address used for authentication and communication.")
    )

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^(?:\+?254|0)?7\d{8}$',
                message=_('Enter a valid Kenyan phone number.')
            )
        ],
        help_text=_("Primary phone number in Kenyan format (07XX XXX XXX).")
    )

    first_name = models.CharField(
        max_length=150,
        help_text=_("User's first name.")
    )

    last_name = models.CharField(
        max_length=150,
        help_text=_("User's last name.")
    )

    national_id = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text=_("Kenyan National ID number.")
    )

    id_verification_status = models.CharField(
        max_length=20,
        choices=IDVerificationStatus.choices,
        default=IDVerificationStatus.UNVERIFIED,
        help_text=_("Current status of identity verification.")
    )

    email_verified = models.BooleanField(
        default=False,
        help_text=_("Whether the user's email has been verified.")
    )

    phone_verified = models.BooleanField(
        default=False,
        help_text=_("Whether the user's phone number has been verified.")
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Designates whether this user should be treated as active.")
    )

    is_staff = models.BooleanField(
        default=False,
        help_text=_("Designates whether the user can log into the admin site.")
    )

    is_superuser = models.BooleanField(
        default=False,
        help_text=_("Designates that this user has all permissions.")
    )

    profile_picture = models.ImageField(
        upload_to='profile_pictures/%Y/%m/',
        null=True,
        blank=True,
        help_text=_("User's profile picture.")
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text=_("User's date of birth for KYC purposes.")
    )

    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text=_("Date and time when the user registered.")
    )

    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address of the user's last login.")
    )

    last_login_device = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Device information from the user's last login.")
    )

    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of consecutive failed login attempts.")
    )

    account_locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp until which the account is locked.")
    )

    totp_secret = models.CharField(
        max_length=32,
        blank=True,
        default='',
        help_text=_("Secret key for Time-based One-Time Password (TOTP).")
    )

    two_factor_enabled = models.BooleanField(
        default=False,
        help_text=_("Whether two-factor authentication is enabled.")
    )

    preferred_language = models.CharField(
        max_length=10,
        default='en',
        choices=[('en', 'English'), ('sw', 'Kiswahili')],
        help_text=_("User's preferred language.")
    )

    notification_preferences = models.JSONField(
        default=dict,
        help_text=_("User's notification preferences for different event types.")
    )

    trust_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text=_("Aggregated trust score based on platform activity (0.00-5.00).")
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
        first_initial = self.first_name[0].upper() if self.first_name else ''
        last_initial = self.last_name[0].upper() if self.last_name else ''
        return f"{first_initial}{last_initial}"

    def has_role(self, role):
        return self.user_roles.filter(role=role, is_active=True).exists()

    def add_role(self, role, assigned_by=None):
        return UserRole.objects.get_or_create(
            user=self,
            role=role,
            defaults={'assigned_by': assigned_by}
        )

    def remove_role(self, role):
        UserRole.objects.filter(user=self, role=role).update(is_active=False)

    def is_account_locked(self):
        if self.account_locked_until and self.account_locked_until > timezone.now():
            return True
        return False

    def increment_failed_login(self):
        from django.conf import settings
        max_attempts = getattr(settings, 'AXES_FAILURE_LIMIT', 5)
        cooloff_minutes = getattr(settings, 'AXES_COOLOFF_TIME', 30)

        self.failed_login_attempts += 1

        if self.failed_login_attempts >= max_attempts:
            self.account_locked_until = timezone.now() + timezone.timedelta(
                minutes=cooloff_minutes
            )

        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])

    def reset_failed_login(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])

    def update_trust_score(self):
        from django.db.models import Q

        completed_transactions = self.created_settlementintent_set.filter(
            state='LEDGER_FINALIZED'
        ).count()

        on_time_contributions = self.contributions.filter(
            status='PAID',
            paid_at__lte=models.F('chama_cycle__end_date')
        ).count()

        loans_repaid = self.loans.filter(
            status='FULLY_REPAID'
        ).count()

        verification_bonus = 1.0 if self.id_verification_status == IDVerificationStatus.VERIFIED else 0.0

        score = min(5.0, (
            (completed_transactions * 0.1) +
            (on_time_contributions * 0.05) +
            (loans_repaid * 0.2) +
            verification_bonus
        ))

        self.trust_score = round(score, 2)
        self.save(update_fields=['trust_score'])


class UserRole(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles',
        help_text=_("The user this role is assigned to.")
    )

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        help_text=_("The role assigned to the user.")
    )

    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='roles_assigned',
        help_text=_("The user who assigned this role.")
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("When the role was assigned.")
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this role assignment is currently active.")
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Optional expiration date for this role.")
    )

    class Meta:
        verbose_name = _('User Role')
        verbose_name_plural = _('User Roles')
        unique_together = ['user', 'role']
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"


class UserProfile(BaseModel, AddressMixin):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text=_("The user this profile belongs to.")
    )

    occupation = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("User's occupation or profession.")
    )

    employer = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("User's employer or business name.")
    )

    monthly_income_range = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Estimated monthly income range for KYC purposes.")
    )

    source_of_funds = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Primary source of funds for KYC/AML compliance.")
    )

    risk_tolerance = models.CharField(
        max_length=20,
        choices=[
            ('CONSERVATIVE', 'Conservative'),
            ('MODERATE', 'Moderate'),
            ('AGGRESSIVE', 'Aggressive'),
        ],
        default='MODERATE',
        help_text=_("User's investment risk tolerance.")
    )

    investment_experience = models.CharField(
        max_length=20,
        choices=[
            ('NONE', 'No Experience'),
            ('BEGINNER', 'Beginner'),
            ('INTERMEDIATE', 'Intermediate'),
            ('EXPERT', 'Expert'),
        ],
        default='BEGINNER',
        help_text=_("User's investment experience level.")
    )

    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')

    def __str__(self):
        return f"Profile: {self.user.get_full_name()}"


class LoginHistory(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        help_text=_("The user who logged in.")
    )

    login_timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text=_("When the login occurred.")
    )

    ip_address = models.GenericIPAddressField(
        help_text=_("IP address used for login.")
    )

    user_agent = models.TextField(
        blank=True,
        default='',
        help_text=_("Browser/device user agent string.")
    )

    device_type = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Type of device used (mobile, desktop, tablet).")
    )

    login_successful = models.BooleanField(
        default=True,
        help_text=_("Whether the login attempt was successful.")
    )

    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Reason for login failure if unsuccessful.")
    )

    location_city = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Approximate city from IP geolocation.")
    )

    class Meta:
        verbose_name = _('Login History')
        verbose_name_plural = _('Login Histories')
        ordering = ['-login_timestamp']

    def __str__(self):
        status = "Success" if self.login_successful else "Failed"
        return f"{self.user.email} - {status} at {self.login_timestamp}"