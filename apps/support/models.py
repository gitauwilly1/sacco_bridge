import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class TicketStatus(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    WAITING_ON_USER = 'WAITING_ON_USER', _('Waiting on User')
    RESOLVED = 'RESOLVED', _('Resolved')
    CLOSED = 'CLOSED', _('Closed')


class TicketPriority(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    URGENT = 'URGENT', _('Urgent')


class TicketCategory(models.TextChoices):
    ACCOUNT = 'ACCOUNT', _('Account & Login')
    CHAMA = 'CHAMA', _('Chama Management')
    INVESTMENT = 'INVESTMENT', _('Investments & Trading')
    PAYMENT = 'PAYMENT', _('Payments & M-Pesa')
    TECHNICAL = 'TECHNICAL', _('Technical Issue')
    FEATURE = 'FEATURE', _('Feature Request')
    OTHER = 'OTHER', _('Other')


class SupportTicket(BaseModel):
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='support_tickets'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(
        max_length=20, choices=TicketCategory.choices, default=TicketCategory.OTHER
    )
    status = models.CharField(
        max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN
    )
    priority = models.CharField(
        max_length=10, choices=TicketPriority.choices, default=TicketPriority.MEDIUM
    )
    assigned_to = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Support Ticket')
        verbose_name_plural = _('Support Tickets')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return f"#{str(self.id)[:8]} - {self.title}"


class SupportMessage(BaseModel):
    ticket = models.ForeignKey(
        SupportTicket, on_delete=models.CASCADE, related_name='messages'
    )
    author = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='ticket_messages'
    )
    message = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text=_("Internal note visible only to support agents")
    )
    attachment = models.FileField(
        upload_to='support_attachments/%Y/%m/%d/', null=True, blank=True
    )

    class Meta:
        verbose_name = _('Ticket Message')
        verbose_name_plural = _('Ticket Messages')
        ordering = ['created_at']

    def __str__(self):
        return f"Message on {self.ticket} by {self.author.get_full_name()}"
