import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class ReportType(models.TextChoices):
    TRANSACTION_HISTORY = 'TRANSACTION_HISTORY', _('Transaction History')
    CONTRIBUTION_REPORT = 'CONTRIBUTION_REPORT', _('Contribution Report')
    LOAN_STATEMENT = 'LOAN_STATEMENT', _('Loan Statement')
    MEMBER_LIST = 'MEMBER_LIST', _('Member List')
    CHAMA_FINANCIAL = 'CHAMA_FINANCIAL', _('Chama Financial Summary')
    DIVIDEND_STATEMENT = 'DIVIDEND_STATEMENT', _('Dividend Statement')
    TAX_STATEMENT = 'TAX_STATEMENT', _('Tax Statement')


class ReportFormat(models.TextChoices):
    CSV = 'CSV', _('CSV')
    PDF = 'PDF', _('PDF')
    EXCEL = 'EXCEL', _('Excel')


class ReportStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    PROCESSING = 'PROCESSING', _('Processing')
    COMPLETED = 'COMPLETED', _('Completed')
    FAILED = 'FAILED', _('Failed')
    EXPIRED = 'EXPIRED', _('Expired')


class ReportRequest(BaseModel):

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='report_requests',
        help_text=_("User who requested the report.")
    )

    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        help_text=_("Type of report requested.")
    )

    report_format = models.CharField(
        max_length=10,
        choices=ReportFormat.choices,
        default=ReportFormat.CSV,
        help_text=_("Output format.")
    )

    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
        help_text=_("Current generation status.")
    )

    title = models.CharField(
        max_length=255,
        help_text=_("Human-readable report title.")
    )

    # Filters applied to this report
    filters = models.JSONField(
        default=dict,
        help_text=_("Filters applied (date range, chama_id, etc.).")
    )

    # Generated file
    report_file = models.FileField(
        upload_to='reports/%Y/%m/',
        null=True,
        blank=True,
        help_text=_("Generated report file.")
    )

    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("File size in bytes.")
    )

    record_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of records in the report.")
    )

    # Timing
    queued_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("When the request was queued.")
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When generation started.")
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When generation completed.")
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the download link expires.")
    )

    # Error handling
    error_message = models.TextField(
        blank=True,
        default='',
        help_text=_("Error details if generation failed.")
    )

    # Celery task ID for tracking
    task_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text=_("Celery task ID for this report.")
    )

    class Meta:
        verbose_name = _('Report Request')
        verbose_name_plural = _('Report Requests')
        ordering = ['-queued_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'queued_at']),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.user.email} ({self.status})"

    def mark_processing(self, task_id):
        self.status = ReportStatus.PROCESSING
        self.started_at = timezone.now()
        self.task_id = task_id
        self.save(update_fields=['status', 'started_at', 'task_id'])

    def mark_completed(self, report_file, file_size, record_count):
        self.status = ReportStatus.COMPLETED
        self.report_file = report_file
        self.file_size = file_size
        self.record_count = record_count
        self.completed_at = timezone.now()
        self.expires_at = timezone.now() + timezone.timedelta(days=7)
        self.save()

    def mark_failed(self, error_message):
        self.status = ReportStatus.FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])