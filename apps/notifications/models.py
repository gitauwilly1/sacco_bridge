from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class NotificationChannel(models.TextChoices):

    IN_APP = 'IN_APP', _('In-App')
    PUSH = 'PUSH', _('Push Notification')
    SMS = 'SMS', _('SMS')
    EMAIL = 'EMAIL', _('Email')


class NotificationPriority(models.TextChoices):

    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    URGENT = 'URGENT', _('Urgent')


class NotificationCategory(models.TextChoices):

    CHAMA_CONTRIBUTION = 'CHAMA_CONTRIBUTION', _('Chama Contribution')
    CHAMA_LOAN = 'CHAMA_LOAN', _('Chama Loan')
    CHAMA_MEETING = 'CHAMA_MEETING', _('Chama Meeting')
    CHAMA_MEMBER = 'CHAMA_MEMBER', _('Chama Member')
    INVESTMENT_OPPORTUNITY = 'INVESTMENT_OPPORTUNITY', _('Investment Opportunity')
    INVESTMENT_OFFER = 'INVESTMENT_OFFER', _('Investment Offer')
    INVESTMENT_CONNECTION = 'INVESTMENT_CONNECTION', _('Investment Connection')
    SETTLEMENT = 'SETTLEMENT', _('Settlement')
    SETTLEMENT_STATUS = 'SETTLEMENT_STATUS', _('Settlement Status Update')
    DISPUTE = 'DISPUTE', _('Dispute')
    SYSTEM = 'SYSTEM', _('System')
    SECURITY = 'SECURITY', _('Security')
    MARKETING = 'MARKETING', _('Marketing')


class DeliveryStatus(models.TextChoices):

    PENDING = 'PENDING', _('Pending')
    SENT = 'SENT', _('Sent')
    DELIVERED = 'DELIVERED', _('Delivered')
    FAILED = 'FAILED', _('Failed')
    READ = 'READ', _('Read')


class NotificationTemplate(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Unique template identifier.")
    )

    category = models.CharField(
        max_length=50,
        choices=NotificationCategory.choices,
        help_text=_("Category this template belongs to.")
    )

    title_template = models.CharField(
        max_length=255,
        help_text=_("Template for notification title. Use {variable} placeholders.")
    )

    body_template = models.TextField(
        help_text=_("Template for notification body. Use {variable} placeholders.")
    )

    sms_template = models.TextField(
        blank=True,
        default='',
        help_text=_("Short SMS version of the template (160 chars max).")
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
        help_text=_("Default priority level.")
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this template is active.")
    )

    sw_title_template = models.CharField(
        max_length=255, blank=True, default='',
        help_text=_("Swahili title template.")
    )
    sw_body_template = models.TextField(
        blank=True, default='',
        help_text=_("Swahili body template.")
    )
    sw_sms_template = models.TextField(
        blank=True, default='',
        help_text=_("Swahili SMS template (160 chars max).")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def render(self, context, language='en'):
        if language == 'sw' and self.sw_title_template:
            title_tpl = self.sw_title_template
            body_tpl = self.sw_body_template
            sms_tpl = self.sw_sms_template
        else:
            title_tpl = self.title_template
            body_tpl = self.body_template
            sms_tpl = self.sms_template

        rendered_title = title_tpl
        rendered_body = body_tpl
        rendered_sms = sms_tpl

        for key, value in context.items():
            placeholder = '{' + key + '}'
            rendered_title = rendered_title.replace(placeholder, str(value))
            rendered_body = rendered_body.replace(placeholder, str(value))
            rendered_sms = rendered_sms.replace(placeholder, str(value))

        return {
            'title': rendered_title,
            'body': rendered_body,
            'sms': rendered_sms,
            'email_subject': rendered_title,
            'email_body': rendered_body,
        }

class Notification(BaseModel):

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text=_("The recipient user.")
    )

    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text=_("Template used to generate this notification.")
    )

    category = models.CharField(
        max_length=50,
        choices=NotificationCategory.choices,
        help_text=_("Notification category.")
    )

    priority = models.CharField(
        max_length=10,
        choices=NotificationPriority.choices,
        default=NotificationPriority.MEDIUM,
        help_text=_("Priority level.")
    )

    title = models.CharField(
        max_length=255,
        help_text=_("Notification title.")
    )

    body = models.TextField(
        help_text=_("Notification body text.")
    )

    action_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text=_("Deep link or URL for notification action.")
    )

    action_text = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Text for the action button.")
    )

    image_url = models.URLField(
        blank=True,
        default='',
        help_text=_("Optional image URL for rich notifications.")
    )

    data = models.JSONField(
        default=dict,
        help_text=_("Additional structured data for the notification.")
    )

    is_read = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether the notification has been read.")
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the notification was read.")
    )

    channels_sent = models.JSONField(
        default=list,
        help_text=_("Channels this notification was sent to.")
    )

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])


class NotificationDelivery(models.Model):

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='deliveries',
        help_text=_("The notification being delivered.")
    )

    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        help_text=_("Delivery channel.")
    )

    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        help_text=_("Current delivery status.")
    )

    recipient = models.CharField(
        max_length=255,
        help_text=_("Recipient address (email, phone, or device token).")
    )

    # Idempotency key: prevents duplicate deliveries
    idempotency_key = models.CharField(
        max_length=128,
        blank=True,
        default='',
        db_index=True,
        help_text=_("Unique key to prevent duplicate delivery attempts.")
    )

    provider_message_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Message ID from the delivery provider.")
    )

    provider_response = models.JSONField(
        default=dict,
        help_text=_("Raw response from the delivery provider.")
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the notification was sent.")
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When delivery was confirmed.")
    )

    error_message = models.TextField(
        blank=True,
        default='',
        help_text=_("Error message if delivery failed.")
    )

    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of delivery retries.")
    )

    class Meta:
        verbose_name = _('Notification Delivery')
        verbose_name_plural = _('Notification Deliveries')
        ordering = ['-sent_at']
        constraints = [
            models.UniqueConstraint(
                fields=['notification', 'channel'],
                name='unique_notification_channel_delivery'
            )
        ]

    def __str__(self):
        return f"Delivery: {self.notification.id} via {self.get_channel_display()} ({self.status})"

class UserDevice(models.Model):

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='devices',
        help_text=_("The user who owns this device.")
    )

    firebase_token = models.CharField(
        max_length=500,
        unique=True,
        help_text=_("Firebase Cloud Messaging registration token.")
    )

    device_type = models.CharField(
        max_length=20,
        choices=[
            ('ANDROID', 'Android'),
            ('IOS', 'iOS'),
            ('WEB', 'Web'),
        ],
        help_text=_("Type of device.")
    )

    device_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Human-readable device name.")
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether this device is currently active.")
    )

    last_active_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("Last time this device was active.")
    )

    app_version = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text=_("App version installed on the device.")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('User Device')
        verbose_name_plural = _('User Devices')
        ordering = ['-last_active_at']

    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.device_name})"


class NotificationPreference(models.Model):

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='notif_preferences',
        help_text=_("The user.")
    )

    category = models.CharField(
        max_length=50,
        choices=NotificationCategory.choices,
        help_text=_("Notification category.")
    )

    in_app_enabled = models.BooleanField(
        default=True,
        help_text=_("Receive in-app notifications for this category.")
    )

    push_enabled = models.BooleanField(
        default=True,
        help_text=_("Receive push notifications for this category.")
    )

    sms_enabled = models.BooleanField(
        default=False,
        help_text=_("Receive SMS notifications for this category.")
    )

    email_enabled = models.BooleanField(
        default=False,
        help_text=_("Receive email notifications for this category.")
    )

    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Start of quiet hours (no push notifications).")
    )

    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        help_text=_("End of quiet hours.")
    )

    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
        unique_together = ['user', 'category']

    def __str__(self):
        return f"{self.user.email} - {self.get_category_display()}"