import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ActivityType(models.TextChoices):

    # Chama activities
    CHAMA_CREATED = 'CHAMA_CREATED', _('Chama created')
    CHAMA_JOINED = 'CHAMA_JOINED', _('Joined chama')
    CHAMA_LEFT = 'CHAMA_LEFT', _('Left chama')
    CONTRIBUTION_MADE = 'CONTRIBUTION_MADE', _('Contribution made')
    CONTRIBUTION_VERIFIED = 'CONTRIBUTION_VERIFIED', _('Contribution verified')
    LOAN_APPLIED = 'LOAN_APPLIED', _('Loan applied')
    LOAN_APPROVED = 'LOAN_APPROVED', _('Loan approved')
    LOAN_DISBURSED = 'LOAN_DISBURSED', _('Loan disbursed')
    LOAN_REPAID = 'LOAN_REPAID', _('Loan repaid')
    MEETING_SCHEDULED = 'MEETING_SCHEDULED', _('Meeting scheduled')
    ATTENDANCE_RECORDED = 'ATTENDANCE_RECORDED', _('Attendance recorded')

    # Investment activities
    LIQUIDITY_REQUESTED = 'LIQUIDITY_REQUESTED', _('Liquidity requested')
    INTEREST_EXPRESSED = 'INTEREST_EXPRESSED', _('Interest expressed')
    OFFER_MADE = 'OFFER_MADE', _('Offer made')
    OFFER_ACCEPTED = 'OFFER_ACCEPTED', _('Offer accepted')
    OFFER_DECLINED = 'OFFER_DECLINED', _('Offer declined')
    OFFER_COUNTERED = 'OFFER_COUNTERED', _('Offer countered')

    # Settlement activities
    SETTLEMENT_INITIATED = 'SETTLEMENT_INITIATED', _('Settlement initiated')
    SETTLEMENT_COMPLETED = 'SETTLEMENT_COMPLETED', _('Settlement completed')
    SETTLEMENT_DISPUTED = 'SETTLEMENT_DISPUTED', _('Settlement disputed')
    SETTLEMENT_RESOLVED = 'SETTLEMENT_RESOLVED', _('Settlement resolved')

    # Account activities
    ACCOUNT_REGISTERED = 'ACCOUNT_REGISTERED', _('Account registered')
    PROFILE_UPDATED = 'PROFILE_UPDATED', _('Profile updated')
    VERIFICATION_COMPLETED = 'VERIFICATION_COMPLETED', _('Verification completed')
    TWO_FACTOR_ENABLED = 'TWO_FACTOR_ENABLED', _('2FA enabled')
    TWO_FACTOR_DISABLED = 'TWO_FACTOR_DISABLED', _('2FA disabled')
    PASSWORD_CHANGED = 'PASSWORD_CHANGED', _('Password changed')


class ActivityLog(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='activities',
        db_index=True,
        help_text=_("User who performed the action.")
    )

    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices,
        db_index=True,
        help_text=_("Type of activity.")
    )

    title = models.CharField(
        max_length=255,
        help_text=_("Human-readable activity title.")
    )

    description = models.TextField(
        blank=True,
        default='',
        help_text=_("Detailed activity description.")
    )

    # Related object references for navigation
    chama = models.ForeignKey(
        'chamas.Chama',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        help_text=_("Related chama if applicable.")
    )

    sacco = models.ForeignKey(
        'investments.SACCO',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        help_text=_("Related SACCO if applicable.")
    )

    # Generic reference fields
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=_("UUID of the related object (contribution, loan, settlement, etc.).")
    )

    reference_type = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Type of the related object (Contribution, Loan, etc.).")
    )

    # Metadata
    metadata = models.JSONField(
        default=dict,
        help_text=_("Additional contextual data (amounts, names, etc.).")
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        editable=False,
        help_text=_("When the activity occurred.")
    )

    class Meta:
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
            models.Index(fields=['chama', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_activity_type_display()}"

    @classmethod
    def log(cls, user, activity_type, title, description='', chama=None,
            sacco=None, reference_id=None, reference_type='', metadata=None):
        return cls.objects.create(
            user=user,
            activity_type=activity_type,
            title=title,
            description=description,
            chama=chama,
            sacco=sacco,
            reference_id=reference_id,
            reference_type=reference_type,
            metadata=metadata or {},
        )