from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class ReportType(models.TextChoices):

    PLATFORM_OVERVIEW = 'PLATFORM_OVERVIEW', _('Platform Overview')
    CHAMA_PERFORMANCE = 'CHAMA_PERFORMANCE', _('Chama Performance')
    INVESTMENT_ACTIVITY = 'INVESTMENT_ACTIVITY', _('Investment Activity')
    SACCO_MARKET = 'SACCO_MARKET', _('SACCO Market')
    SETTLEMENT_AUDIT = 'SETTLEMENT_AUDIT', _('Settlement Audit')
    DISPUTE_ANALYSIS = 'DISPUTE_ANALYSIS', _('Dispute Analysis')
    USER_GROWTH = 'USER_GROWTH', _('User Growth')
    REVENUE = 'REVENUE', _('Revenue Report')


class ReportFrequency(models.TextChoices):

    DAILY = 'DAILY', _('Daily')
    WEEKLY = 'WEEKLY', _('Weekly')
    MONTHLY = 'MONTHLY', _('Monthly')
    QUARTERLY = 'QUARTERLY', _('Quarterly')


class ExportFormat(models.TextChoices):

    CSV = 'CSV', _('CSV')
    PDF = 'PDF', _('PDF')
    EXCEL = 'EXCEL', _('Excel')
    JSON = 'JSON', _('JSON')


class PlatformMetric(BaseModel):

    metric_date = models.DateField(
        db_index=True,
        help_text=_("Date this metric represents.")
    )

    # User Metrics
    total_users = models.PositiveIntegerField(
        default=0,
        help_text=_("Total registered users.")
    )

    new_users = models.PositiveIntegerField(
        default=0,
        help_text=_("New users registered on this date.")
    )

    verified_users = models.PositiveIntegerField(
        default=0,
        help_text=_("Users with verified identity.")
    )

    active_users = models.PositiveIntegerField(
        default=0,
        help_text=_("Users active on this date.")
    )

    # Chama Metrics
    total_chamas = models.PositiveIntegerField(
        default=0,
        help_text=_("Total active chamas.")
    )

    new_chamas = models.PositiveIntegerField(
        default=0,
        help_text=_("New chamas created on this date.")
    )

    total_chama_members = models.PositiveIntegerField(
        default=0,
        help_text=_("Total chama memberships.")
    )

    total_chama_savings = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total savings across all chamas.")
    )

    total_chama_loans = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total outstanding chama loans.")
    )

    # Investment Metrics
    total_liquidity_requests = models.PositiveIntegerField(
        default=0,
        help_text=_("Total liquidity requests created.")
    )

    active_liquidity_requests = models.PositiveIntegerField(
        default=0,
        help_text=_("Currently active liquidity requests.")
    )

    total_connections = models.PositiveIntegerField(
        default=0,
        help_text=_("Total buyer-seller connections.")
    )

    # Settlement Metrics
    total_settlements = models.PositiveIntegerField(
        default=0,
        help_text=_("Total settlements initiated.")
    )

    completed_settlements = models.PositiveIntegerField(
        default=0,
        help_text=_("Successfully completed settlements.")
    )

    reversed_settlements = models.PositiveIntegerField(
        default=0,
        help_text=_("Reversed settlements.")
    )

    disputed_settlements = models.PositiveIntegerField(
        default=0,
        help_text=_("Settlements in dispute.")
    )

    total_settlement_volume = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total value of completed settlements.")
    )

    # Revenue Metrics
    total_platform_fees = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Total platform fees collected.")
    )

    total_premium_revenue = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        help_text=_("Revenue from premium chama subscriptions.")
    )

    # SACCO Metrics
    total_saccos = models.PositiveIntegerField(
        default=0,
        help_text=_("Total verified SACCOs on platform.")
    )

    active_saccos = models.PositiveIntegerField(
        default=0,
        help_text=_("SACCOs with active trading.")
    )

    class Meta:
        verbose_name = _('Platform Metric')
        verbose_name_plural = _('Platform Metrics')
        ordering = ['-metric_date']
        unique_together = ['metric_date']
        indexes = [
            models.Index(fields=['metric_date']),
        ]

    def __str__(self):
        return f"Platform Metrics - {self.metric_date}"


class ChamaAnalytics(BaseModel):

    chama = models.ForeignKey(
        'chamas.Chama',
        on_delete=models.CASCADE,
        related_name='analytics',
        help_text=_("The chama these analytics belong to.")
    )

    period_start = models.DateField(
        help_text=_("Start date of the analytics period.")
    )

    period_end = models.DateField(
        help_text=_("End date of the analytics period.")
    )

    period_type = models.CharField(
        max_length=20,
        choices=[
            ('WEEKLY', 'Weekly'),
            ('MONTHLY', 'Monthly'),
            ('QUARTERLY', 'Quarterly'),
            ('ANNUAL', 'Annual'),
        ],
        default='MONTHLY',
        help_text=_("Type of analytics period.")
    )

    # Membership Metrics
    total_members = models.PositiveIntegerField(default=0)
    new_members = models.PositiveIntegerField(default=0)
    members_left = models.PositiveIntegerField(default=0)
    active_members = models.PositiveIntegerField(default=0)

    # Contribution Metrics
    total_contributions = models.DecimalField(
        max_digits=20, decimal_places=2, default=0
    )
    average_contribution = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    on_time_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text=_("Percentage of on-time contributions.")
    )
    late_contributions = models.PositiveIntegerField(default=0)
    missed_contributions = models.PositiveIntegerField(default=0)
    total_late_fees = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )

    # Loan Metrics
    total_loans_issued = models.PositiveIntegerField(default=0)
    total_loan_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=0
    )
    total_interest_earned = models.DecimalField(
        max_digits=20, decimal_places=2, default=0
    )
    loans_fully_repaid = models.PositiveIntegerField(default=0)
    loans_in_default = models.PositiveIntegerField(default=0)
    default_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    # Meeting Metrics
    total_meetings = models.PositiveIntegerField(default=0)
    average_attendance = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text=_("Average meeting attendance percentage.")
    )

    # Financial Health
    savings_growth = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text=_("Percentage growth in savings.")
    )
    loan_to_savings_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    class Meta:
        verbose_name = _('Chama Analytics')
        verbose_name_plural = _('Chama Analytics')
        ordering = ['-period_end']
        unique_together = ['chama', 'period_start', 'period_end']
        indexes = [
            models.Index(fields=['chama', 'period_end']),
        ]

    def __str__(self):
        return f"{self.chama.name} Analytics - {self.period_end}"


class SACCOMarketAnalytics(BaseModel):

    sacco = models.ForeignKey(
        'investments.SACCO',
        on_delete=models.CASCADE,
        related_name='market_analytics',
        help_text=_("The SACCO these analytics belong to.")
    )

    metric_date = models.DateField(
        db_index=True,
        help_text=_("Date of these metrics.")
    )

    # Price Metrics
    average_price_per_share = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    highest_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    lowest_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    opening_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    closing_price = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )

    # Volume Metrics
    total_volume_shares = models.DecimalField(
        max_digits=20, decimal_places=4, default=0
    )
    total_volume_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=0
    )
    number_of_transactions = models.PositiveIntegerField(default=0)

    # Liquidity Metrics
    active_sellers = models.PositiveIntegerField(default=0)
    active_buyers = models.PositiveIntegerField(default=0)
    average_time_to_match = models.PositiveIntegerField(
        default=0,
        help_text=_("Average seconds to match a liquidity request.")
    )

    # Spread Metrics
    average_buyer_offer = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    average_seller_ask = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    average_spread = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = _('SACCO Market Analytics')
        verbose_name_plural = _('SACCO Market Analytics')
        ordering = ['-metric_date']
        unique_together = ['sacco', 'metric_date']
        indexes = [
            models.Index(fields=['sacco', 'metric_date']),
        ]

    def __str__(self):
        return f"{self.sacco.name} Market - {self.metric_date}"


class ScheduledReport(BaseModel):

    name = models.CharField(
        max_length=255,
        help_text=_("Name of the scheduled report.")
    )

    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        help_text=_("Type of report to generate.")
    )

    frequency = models.CharField(
        max_length=20,
        choices=ReportFrequency.choices,
        default=ReportFrequency.MONTHLY,
        help_text=_("How often the report is generated.")
    )

    export_format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.PDF,
        help_text=_("Format for the exported report.")
    )

    recipients = models.JSONField(
        default=list,
        help_text=_("List of email addresses to send the report to.")
    )

    parameters = models.JSONField(
        default=dict,
        help_text=_("Custom parameters for report generation.")
    )

    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this scheduled report is active.")
    )

    last_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the report was last generated.")
    )

    next_generation_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the report will next be generated.")
    )

    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='scheduled_reports',
        help_text=_("Who created this scheduled report.")
    )

    class Meta:
        verbose_name = _('Scheduled Report')
        verbose_name_plural = _('Scheduled Reports')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class ReportGeneration(BaseModel):

    scheduled_report = models.ForeignKey(
        ScheduledReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generations',
        help_text=_("The scheduled report that triggered this generation.")
    )

    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        help_text=_("Type of report generated.")
    )

    export_format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        help_text=_("Export format used.")
    )

    file = models.FileField(
        upload_to='reports/%Y/%m/',
        null=True,
        blank=True,
        help_text=_("Generated report file.")
    )

    parameters = models.JSONField(
        default=dict,
        help_text=_("Parameters used for generation.")
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('GENERATING', 'Generating'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING',
        help_text=_("Generation status.")
    )

    error_message = models.TextField(
        blank=True,
        default='',
        help_text=_("Error message if generation failed.")
    )

    generated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_reports',
        help_text=_("Who requested this report.")
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When generation completed.")
    )

    class Meta:
        verbose_name = _('Report Generation')
        verbose_name_plural = _('Report Generations')
        ordering = ['-created_at']

    def __str__(self):
        return f"Report {self.id} - {self.get_report_type_display()} ({self.status})"