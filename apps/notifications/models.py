import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class NotificationChannel(models.TextChoices):

    PUSH = 'PUSH', _('Push Notification')
    SMS = 'SMS', _('SMS')
    EMAIL = 'EMAIL', _('Email')
    IN_APP = 'IN_APP', _('In-App Notification')


class NotificationPriority(models.TextChoices):

    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    URGENT = 'URGENT', _('Urgent')


class NotificationCategory(models.TextChoices):

    CHAMA_CONTRIBUTION = 'CHAMA_CONTRIBUTION', _('Chama Contribution')
    CHAMA_LOAN = 'CHAMA_LOAN', _('Chama Loan')
    CHAMA_MEETING = 'CHAMA_MEETING', _('Chama Meeting')
    CHAMA_ANNOUNCEMENT = 'CHAMA_ANNOUNCEMENT', _('Chama Announcement')
    SETTLEMENT = 'SETTLEMENT', _('Settlement')
    LIQUIDITY_REQUEST = 'LIQUIDITY_REQUEST', _('Liquidity Request')
    CONNECTION = 'CONNECTION', _('Buyer-Seller Connection')
    OFFER = 'OFFER', _('Offer')
    DISPUTE = 'DISPUTE', _('Dispute')
    ACCOUNT = 'ACCOUNT', _('Account')
    SECURITY = 'SECURITY', _('Security')
    SYSTEM = 'SYSTEM', _('System')


class NotificationStatus(models.TextChoices):
    """Delivery status of a notification."""

    PENDING = 'PENDING', _('Pending')
    SENT = 'SENT', _('Sent')
    DELIVERED = 'DELIVERED', _('Delivered')
    READ = 'READ', _('Read')
    FAILED = 'FAILED', _('Failed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class DevicePlatform(models.TextChoices):
    """Mobile device platforms."""

    ANDROID = 'ANDROID', _('Android')
    IOS = 'IOS', _('iOS')
    WEB = 'WEB', _('Web')


class Notification(BaseModel):

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text=_("The recipient user.")
    )

    category = models.CharField(
        max_length=30,
        choices=NotificationCategory.choices,
        help_text=_("Category of the notification.")
    )

    priority = models.CharField(
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.MEDIUM,
        help_text=_("Priority level of the notification.")
    )

    title = models.CharField(
        max_length=255,
        help_text=_("Notification title.")
    )

    body = models.TextField(
        help_text=_("Notification body content.")
    )

    short_message = models.CharField(
        max_length=160,
        blank=True,
        default='',
        help_text=_("Short version for SMS (max 160 chars).")
    )

    channel = models.CharField(
        max_length=10,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
        help_text=_("Primary delivery channel.")
    )

    status = models.CharField(
        max_length=15,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
        help_text=_("Current delivery status.")
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the notification was sent.")
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the notification was delivered to device.")
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the user read the notification.")
    )

    action_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text=_("Deep link URL for notification action.")
    )

    action_text = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Text for the action button.")
    )

    data = models.JSONField(
        default=dict,
        help_text=_("Additional structured data for the notification.")
    )

    reference_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Reference to the related entity (settlement, loan, etc.).")
    )

    reference_type = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Type of the referenced entity.")
    )

    external_message_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("External message ID (Firebase message ID, SMS ID, etc.).")
    )

    error_message = models.TextField(
        blank=True,
        default='',
        help_text=_("Error message if delivery failed.")
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of delivery retry attempts.")
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'read_at']),
            models.Index(fields=['category']),
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['reference_id', 'reference_type']),
        ]

    def __str__(self):
        return f"Notification: {self.title} - {self.user.email} ({self.status})"

    def mark_as_sent(self, external_id=''):
        """Mark notification as sent."""
        self.status = NotificationStatus.SENT
        self.sent_at = timezone.now()
        if external_id:
            self.external_message_id = external_id
        self.save(update_fields=['status', 'sent_at', 'external_message_id'])

    def mark_as_delivered(self):
        """Mark notification as delivered to device."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])

    def mark_as_read(self):
        """Mark notification as read by user."""
        self.status = NotificationStatus.READ
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at'])

    def mark_as_failed(self, error_message=''):
        """Mark notification delivery as failed."""
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])


class UserDevice(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='devices',
        help_text=_("The user who owns this device.")
    )

    fcm_token = models.CharField(
        max_length=500,
        unique=True,
        help_text=_("Firebase Cloud Messaging registration token.")
    )

    platform = models.CharField(
        max_length=10,
        choices=DevicePlatform.choices,
        default=DevicePlatform.ANDROID,
        help_text=_("Device platform.")
    )

    device_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Human-readable device name.")
    )

    device_model = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Device model information.")
    )

    app_version = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text=_("Installed app version.")
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether this device is currently active for notifications.")
    )

    last_active_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Last time this device was active.")
    )

    registered_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("When this device was first registered.")
    )

    class Meta:
        verbose_name = _('User Device')
        verbose_name_plural = _('User Devices')
        ordering = ['-last_active_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['fcm_token']),
            models.Index(fields=['platform']),
        ]

    def __str__(self):
        return f"Device: {self.device_name} ({self.get_platform_display()}) - {self.user.email}"


class NotificationPreference(models.Model):

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text=_("The user these preferences belong to.")
    )

    category = models.CharField(
        max_length=30,
        choices=NotificationCategory.choices,
        help_text=_("Notification category.")
    )

    channel = models.CharField(
        max_length=10,
        choices=NotificationChannel.choices,
        help_text=_("Delivery channel.")
    )

    enabled = models.BooleanField(
        default=True,
        help_text=_("Whether this notification type is enabled.")
    )

    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
        unique_together = ['user', 'category', 'channel']
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'enabled']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.get_category_display()} via {self.get_channel_display()}"


class NotificationTemplate(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Template identifier name.")
    )

    category = models.CharField(
        max_length=30,
        choices=NotificationCategory.choices,
        help_text=_("Category this template belongs to.")
    )

    title_template = models.CharField(
        max_length=255,
        help_text=_("Template for notification title with {variable} placeholders.")
    )

    body_template = models.TextField(
        help_text=_("Template for notification body with {variable} placeholders.")
    )

    sms_template = models.CharField(
        max_length=160,
        blank=True,
        default='',
        help_text=_("Short SMS template (max 160 chars).")
    )

    email_subject_template = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Email subject line template.")
    )

    email_body_template = models.TextField(
        blank=True,
        default='',
        help_text=_("HTML email body template.")
    )

    default_channels = models.JSONField(
        default=list,
        help_text=_("Default delivery channels for this template.")
    )

    default_priority = models.CharField(
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.MEDIUM,
        help_text=_("Default priority for this notification type.")
    )

    action_url_template = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text=_("Template for deep link URL.")
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this template is active.")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ['category', 'name']

    def __str__(self):
        return f"Template: {self.name} ({self.get_category_display()})"

    def render(self, context):
        return {
            'title': self.title_template.format(**context),
            'body': self.body_template.format(**context),
            'sms': self.sms_template.format(**context) if self.sms_template else '',
            'email_subject': self.email_subject_template.format(**context) if self.email_subject_template else '',
            'email_body': self.email_body_template.format(**context) if self.email_body_template else '',
            'action_url': self.action_url_template.format(**context) if self.action_url_template else '',
        }