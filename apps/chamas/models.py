import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import BaseModel
from apps.core.validators import validate_positive_amount, validate_percentage


class ChamaStatus(models.TextChoices):

    ACTIVE = 'ACTIVE', _('Active')
    INACTIVE = 'INACTIVE', _('Inactive')
    SUSPENDED = 'SUSPENDED', _('Suspended')
    ARCHIVED = 'ARCHIVED', _('Archived')


class ChamaType(models.TextChoices):

    WELFARE_GROUP = 'WELFARE_GROUP', _('Welfare Group')
    INVESTMENT_CLUB = 'INVESTMENT_CLUB', _('Investment Club')
    MERRY_GO_ROUND = 'MERRY_GO_ROUND', _('Merry-Go-Round')
    TABLE_BANKING = 'TABLE_BANKING', _('Table Banking')
    FAMILY_GROUP = 'FAMILY_GROUP', _('Family Group')
    OTHER = 'OTHER', _('Other')


class ContributionFrequency(models.TextChoices):

    DAILY = 'DAILY', _('Daily')
    WEEKLY = 'WEEKLY', _('Weekly')
    BIWEEKLY = 'BIWEEKLY', _('Bi-Weekly')
    MONTHLY = 'MONTHLY', _('Monthly')
    PER_MEETING = 'PER_MEETING', _('Per Meeting')


class MemberRole(models.TextChoices):

    CHAIRPERSON = 'CHAIRPERSON', _('Chairperson')
    TREASURER = 'TREASURER', _('Treasurer')
    SECRETARY = 'SECRETARY', _('Secretary')
    VICE_CHAIRPERSON = 'VICE_CHAIRPERSON', _('Vice Chairperson')
    LOAN_OFFICER = 'LOAN_OFFICER', _('Loan Officer')
    MEMBER = 'MEMBER', _('Member')


class ContributionStatus(models.TextChoices):

    PENDING = 'PENDING', _('Pending')
    PAID = 'PAID', _('Paid')
    LATE = 'LATE', _('Late')
    MISSED = 'MISSED', _('Missed')
    WAIVED = 'WAIVED', _('Waived')
    REFUNDED = 'REFUNDED', _('Refunded')


class PaymentMethod(models.TextChoices):

    MPESA = 'MPESA', _('M-Pesa')
    CASH = 'CASH', _('Cash')
    BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
    OTHER = 'OTHER', _('Other')


class LoanStatus(models.TextChoices):

    PENDING = 'PENDING', _('Pending Review')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    DISBURSED = 'DISBURSED', _('Disbursed')
    PARTIALLY_REPAID = 'PARTIALLY_REPAID', _('Partially Repaid')
    FULLY_REPAID = 'FULLY_REPAID', _('Fully Repaid')
    DEFAULTED = 'DEFAULTED', _('Defaulted')
    WRITTEN_OFF = 'WRITTEN_OFF', _('Written Off')


class MeetingStatus(models.TextChoices):

    SCHEDULED = 'SCHEDULED', _('Scheduled')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    COMPLETED = 'COMPLETED', _('Completed')
    CANCELLED = 'CANCELLED', _('Cancelled')
    POSTPONED = 'POSTPONED', _('Postponed')


class Chama(BaseModel):

    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text=_("Name of the chama group.")
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("URL-friendly identifier for the chama.")
    )

    description = models.TextField(
        blank=True,
        default='',
        help_text=_("Description of the chama's purpose and activities.")
    )

    chama_type = models.CharField(
        max_length=30,
        choices=ChamaType.choices,
        default=ChamaType.OTHER,
        help_text=_("Type classification of the chama.")
    )

    status = models.CharField(
        max_length=20,
        choices=ChamaStatus.choices,
        default=ChamaStatus.ACTIVE,
        db_index=True,
        help_text=_("Current operational status of the chama.")
    )

    invite_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Unique code for members to join the chama.")
    )

    contribution_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Standard contribution amount per period.")
    )

    contribution_frequency = models.CharField(
        max_length=20,
        choices=ContributionFrequency.choices,
        default=ContributionFrequency.WEEKLY,
        help_text=_("How often contributions are made.")
    )

    max_members = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(2), MaxValueValidator(5000)],
        help_text=_("Maximum number of members allowed.")
    )

    total_savings = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total accumulated savings in the chama.")
    )

    available_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Currently available funds not tied up in loans.")
    )

    outstanding_loans = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total outstanding loan principal.")
    )

    # M-Pesa Integration
    mpesa_paybill = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text=_("M-Pesa Paybill number for contributions.")
    )

    mpesa_account_reference = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text=_("Account reference for M-Pesa payments.")
    )

    auto_verify_mpesa = models.BooleanField(
        default=False,
        help_text=_("Automatically verify contributions from M-Pesa callbacks.")
    )

    # Loan Configuration
    loan_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[validate_percentage],
        help_text=_("Standard interest rate for loans (percentage).")
    )

    max_loan_multiple = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('3.00'),
        help_text=_("Maximum loan amount as multiple of total contributions.")
    )

    max_loan_duration_months = models.PositiveIntegerField(
        default=12,
        help_text=_("Maximum loan repayment period in months.")
    )

    require_guarantors = models.BooleanField(
        default=False,
        help_text=_("Whether loans require guarantors.")
    )

    min_guarantors = models.PositiveIntegerField(
        default=1,
        help_text=_("Minimum number of guarantors required if enabled.")
    )

    loan_approval_method = models.CharField(
        max_length=30,
        choices=[
            ('GROUP_VOTE', 'Group Vote'),
            ('LOAN_COMMITTEE', 'Loan Committee'),
            ('TREASURER', 'Treasurer Discretion'),
        ],
        default='GROUP_VOTE',
        help_text=_("Method used to approve loan requests.")
    )

    # Payout Configuration
    payout_cycle_months = models.PositiveIntegerField(
        default=12,
        help_text=_("Number of months in a payout cycle.")
    )

    payout_method = models.CharField(
        max_length=30,
        choices=[
            ('EQUAL', 'Equal Distribution'),
            ('PROPORTIONAL', 'Proportional to Contributions'),
            ('ROTATING', 'Rotating (Merry-Go-Round)'),
        ],
        default='EQUAL',
        help_text=_("Method for distributing payouts.")
    )

    next_payout_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Expected date of next payout distribution.")
    )

    # Late Payment Configuration
    late_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Fee charged for late contributions.")
    )

    grace_period_days = models.PositiveIntegerField(
        default=3,
        help_text=_("Grace period before late fee applies.")
    )

    # Settings
    allow_member_contributions = models.BooleanField(
        default=True,
        help_text=_("Whether members can self-record contributions.")
    )

    require_contribution_verification = models.BooleanField(
        default=False,
        help_text=_("Whether contributions require verification by officials.")
    )

    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_chamas',
        help_text=_("User who created the chama.")
    )

    health_score = models.DecimalField(
    max_digits=4, decimal_places=1, default=0.0,
    help_text=_("Overall chama health score (0.0-100.0).")
    )
    health_score_grade = models.CharField(
        max_length=3, blank=True, default='',
        help_text=_("Letter grade (A+, A, B, C, D, F).")
    )
    health_score_breakdown = models.JSONField(
        default=dict,
        help_text=_("Breakdown of score components.")
    )
    health_score_updated_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When the health score was last calculated.")
    )

    class Meta:
        verbose_name = _('Chama')
        verbose_name_plural = _('Chamas')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['invite_code']),
            models.Index(fields=['status']),
            models.Index(fields=['chama_type']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Chama.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if not self.invite_code:
            self.invite_code = self._generate_invite_code()
        super().save(*args, **kwargs)

    def _generate_invite_code(self):
        """Generate a unique invite code."""
        import random
        import string
        prefix = ''.join(random.choices(string.ascii_uppercase, k=4))
        suffix = ''.join(random.choices(string.digits, k=4))
        code = f"{prefix}-{suffix}"
        if Chama.objects.filter(invite_code=code).exists():
            return self._generate_invite_code()
        return code

    def update_financials(self):
        from django.db.models import Sum

        total = self.contributions.filter(
            status=ContributionStatus.PAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        outstanding = self.loans.filter(
            status__in=[LoanStatus.DISBURSED, LoanStatus.PARTIALLY_REPAID]
        ).aggregate(
            total=Sum('outstanding_balance')
        )['total'] or Decimal('0.00')

        self.total_savings = total
        self.outstanding_loans = outstanding
        self.available_balance = total - outstanding
        self.save(update_fields=['total_savings', 'available_balance', 'outstanding_loans'])


class ChamaMember(BaseModel):

    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name='memberships',
        help_text=_("The chama this membership belongs to.")
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='chama_memberships',
        help_text=_("The user who is a member of the chama.")
    )

    role = models.CharField(
        max_length=30,
        choices=MemberRole.choices,
        default=MemberRole.MEMBER,
        help_text=_("Member's role within the chama.")
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether the membership is currently active.")
    )

    joined_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the member joined the chama.")
    )

    left_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the member left the chama.")
    )

    total_contributions = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total amount contributed by this member.")
    )

    current_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Member's current balance in the chama.")
    )

    outstanding_loans = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total outstanding loan balance.")
    )

    contribution_streak = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of consecutive on-time contributions.")
    )

    last_contribution_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date of the member's last contribution.")
    )

    is_overdue = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether the member has overdue contributions.")
    )

    overdue_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Amount of overdue contributions.")
    )

    standing_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Member's standing score (0.00-5.00).")
    )

    class Meta:
        verbose_name = _('Chama Member')
        verbose_name_plural = _('Chama Members')
        unique_together = ['chama', 'user']
        indexes = [
            models.Index(fields=['chama', 'user']),
            models.Index(fields=['chama', 'role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_overdue']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.chama.name} ({self.get_role_display()})"

    def update_standing_score(self):
        total_periods = self.chama.contributions.filter(
            status__in=[ContributionStatus.PAID, ContributionStatus.LATE, ContributionStatus.MISSED]
        ).values('period_start').distinct().count()

        if total_periods == 0:
            return Decimal('0.00')

        on_time = self.contributions.filter(status=ContributionStatus.PAID).count()
        score = min(Decimal('5.00'), Decimal(on_time) / Decimal(total_periods) * Decimal('5.00'))
        self.standing_score = score.quantize(Decimal('0.01'))
        self.save(update_fields=['standing_score'])


class Contribution(BaseModel):

    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name='contributions',
        help_text=_("The chama this contribution belongs to.")
    )

    member = models.ForeignKey(
        ChamaMember,
        on_delete=models.CASCADE,
        related_name='contributions',
        help_text=_("The member making the contribution.")
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Contribution amount.")
    )

    expected_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Expected contribution amount for this period.")
    )

    status = models.CharField(
        max_length=20,
        choices=ContributionStatus.choices,
        default=ContributionStatus.PENDING,
        db_index=True,
        help_text=_("Current status of the contribution.")
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MPESA,
        help_text=_("Method used for payment.")
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("External payment reference (e.g., M-Pesa transaction ID).")
    )

    period_start = models.DateField(
        help_text=_("Start date of the contribution period.")
    )

    period_end = models.DateField(
        help_text=_("End date of the contribution period.")
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the contribution was paid.")
    )

    verified_by = models.ForeignKey(
        ChamaMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_contributions',
        help_text=_("Chama official who verified the contribution.")
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the contribution was verified.")
    )

    notes = models.TextField(
        blank=True,
        default='',
        help_text=_("Optional notes about the contribution.")
    )

    mpesa_receipt = models.TextField(
        blank=True,
        default='',
        help_text=_("Raw M-Pesa callback data for this contribution.")
    )

    class Meta:
        verbose_name = _('Contribution')
        verbose_name_plural = _('Contributions')
        ordering = ['-period_start', '-created_at']
        indexes = [
            models.Index(fields=['chama', 'period_start']),
            models.Index(fields=['member', 'status']),
            models.Index(fields=['chama', 'period_start', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_reference']),
        ]

    def __str__(self):
        return f"{self.member.user.get_full_name()} - KSh {self.amount} ({self.status})"

    def mark_as_paid(self, payment_reference=''):
        self.status = ContributionStatus.PAID
        self.paid_at = timezone.now()
        if payment_reference:
            self.payment_reference = payment_reference
        self.save()

        self.member.total_contributions += self.amount
        self.member.current_balance += self.amount
        self.member.last_contribution_date = timezone.now().date()
        self.member.contribution_streak += 1
        self.member.is_overdue = False
        self.member.overdue_amount = Decimal('0.00')
        self.member.save()

        self.chama.update_financials()
        self.member.update_standing_score()

    def mark_as_late(self):
        self.status = ContributionStatus.LATE
        self.save()
        self.member.is_overdue = True
        self.member.overdue_amount += self.amount
        self.member.contribution_streak = 0
        self.member.save()
        self.member.update_standing_score()


class Loan(BaseModel):

    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name='loans',
        help_text=_("The chama this loan belongs to.")
    )

    borrower = models.ForeignKey(
        ChamaMember,
        on_delete=models.CASCADE,
        related_name='loans',
        help_text=_("The member borrowing the loan.")
    )

    principal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Original loan principal amount.")
    )

    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[validate_percentage],
        help_text=_("Interest rate applied to this loan.")
    )

    duration_months = models.PositiveIntegerField(
        help_text=_("Loan repayment period in months.")
    )

    total_interest = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total interest payable.")
    )

    total_repayable = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Total amount to be repaid (principal + interest).")
    )

    monthly_installment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Monthly installment amount.")
    )

    outstanding_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Remaining balance to be repaid.")
    )

    status = models.CharField(
        max_length=30,
        choices=LoanStatus.choices,
        default=LoanStatus.PENDING,
        db_index=True,
        help_text=_("Current loan status.")
    )

    purpose = models.TextField(
        blank=True,
        default='',
        help_text=_("Purpose of the loan.")
    )

    approved_by = models.ForeignKey(
        ChamaMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_loans',
        help_text=_("Who approved this loan.")
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the loan was approved.")
    )

    disbursed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When funds were disbursed.")
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Final repayment due date.")
    )

    guarantors = models.ManyToManyField(
        ChamaMember,
        blank=True,
        related_name='guaranteed_loans',
        help_text=_("Members who guaranteed this loan.")
    )

    class Meta:
        verbose_name = _('Loan')
        verbose_name_plural = _('Loans')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['chama', 'status']),
            models.Index(fields=['borrower', 'status']),
            models.Index(fields=['chama', 'borrower', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Loan {self.id} - {self.borrower.user.get_full_name()} (KSh {self.principal})"

    def calculate_terms(self):
        from apps.core.utils import calculate_loan_interest

        result = calculate_loan_interest(
            self.principal, self.interest_rate, self.duration_months
        )
        self.total_interest = result['total_interest']
        self.total_repayable = result['total_repayment']
        self.monthly_installment = result['monthly_installment']
        self.outstanding_balance = self.total_repayable
        self.save()

    def approve(self, approved_by):
        self.status = LoanStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.save()

    def disburse(self):
        self.status = LoanStatus.DISBURSED
        self.disbursed_at = timezone.now()
        self.due_date = timezone.now().date() + timezone.timedelta(
            days=self.duration_months * 30
        )

        self.borrower.current_balance += self.principal
        self.borrower.outstanding_loans += self.total_repayable
        self.borrower.save()

        self.chama.available_balance -= self.principal
        self.chama.outstanding_loans += self.total_repayable
        self.chama.save(update_fields=['available_balance', 'outstanding_loans'])
        self.save()

    def record_repayment(self, amount):
        from decimal import Decimal
        amount = Decimal(str(amount))

        self.outstanding_balance -= amount
        if self.outstanding_balance <= Decimal('0.00'):
            self.outstanding_balance = Decimal('0.00')
            self.status = LoanStatus.FULLY_REPAID
        else:
            self.status = LoanStatus.PARTIALLY_REPAID

        self.borrower.outstanding_loans -= amount
        if self.borrower.outstanding_loans < Decimal('0.00'):
            self.borrower.outstanding_loans = Decimal('0.00')
        self.borrower.save()

        self.chama.available_balance += amount
        self.chama.outstanding_loans -= amount
        if self.chama.outstanding_loans < Decimal('0.00'):
            self.chama.outstanding_loans = Decimal('0.00')
        self.chama.save(update_fields=['available_balance', 'outstanding_loans'])
        self.save()


class LoanRepayment(BaseModel):

    loan = models.ForeignKey(
        Loan,
        on_delete=models.CASCADE,
        related_name='repayments',
        help_text=_("The loan this repayment belongs to.")
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Repayment amount.")
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MPESA,
        help_text=_("Payment method used.")
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("External payment reference.")
    )

    paid_at = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the repayment was made.")
    )

    class Meta:
        verbose_name = _('Loan Repayment')
        verbose_name_plural = _('Loan Repayments')
        ordering = ['-paid_at']

    def __str__(self):
        return f"Repayment KSh {self.amount} - Loan {self.loan.id}"


class Meeting(BaseModel):

    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name='meetings',
        help_text=_("The chama this meeting belongs to.")
    )

    title = models.CharField(
        max_length=255,
        help_text=_("Meeting title or topic.")
    )

    description = models.TextField(
        blank=True,
        default='',
        help_text=_("Meeting description or agenda.")
    )

    date = models.DateField(
        help_text=_("Scheduled meeting date.")
    )

    start_time = models.TimeField(
        help_text=_("Meeting start time.")
    )

    end_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Meeting end time.")
    )

    location = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text=_("Meeting location or virtual link.")
    )

    status = models.CharField(
        max_length=20,
        choices=MeetingStatus.choices,
        default=MeetingStatus.SCHEDULED,
        db_index=True,
        help_text=_("Current meeting status.")
    )

    minutes = models.TextField(
        blank=True,
        default='',
        help_text=_("Meeting minutes or notes.")
    )

    organizer = models.ForeignKey(
        ChamaMember,
        on_delete=models.SET_NULL,
        null=True,
        related_name='organized_meetings',
        help_text=_("Member who organized the meeting.")
    )

    class Meta:
        verbose_name = _('Meeting')
        verbose_name_plural = _('Meetings')
        ordering = ['-date', '-start_time']
        indexes = [
            models.Index(fields=['chama', 'date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.chama.name} - {self.title} ({self.date})"


class MeetingAttendance(BaseModel):

    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='attendees',
        help_text=_("The meeting.")
    )

    member = models.ForeignKey(
        ChamaMember,
        on_delete=models.CASCADE,
        related_name='meeting_attendance',
        help_text=_("The member who attended.")
    )

    attended = models.BooleanField(
        default=True,
        help_text=_("Whether the member attended.")
    )

    arrived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When the member arrived.")
    )

    apology = models.TextField(
        blank=True,
        default='',
        help_text=_("Apology or reason for absence.")
    )

    class Meta:
        verbose_name = _('Meeting Attendance')
        verbose_name_plural = _('Meeting Attendances')
        unique_together = ['meeting', 'member']

    def __str__(self):
        status = "Present" if self.attended else "Absent"
        return f"{self.member.user.get_full_name()} - {status}"


class Payout(BaseModel):

    chama = models.ForeignKey(
        Chama,
        on_delete=models.CASCADE,
        related_name='payouts',
        help_text=_("The chama this payout belongs to.")
    )

    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Total amount distributed.")
    )

    payout_date = models.DateField(
        help_text=_("Date of payout distribution.")
    )

    cycle_start = models.DateField(
        help_text=_("Start date of the payout cycle.")
    )

    cycle_end = models.DateField(
        help_text=_("End date of the payout cycle.")
    )

    payout_method = models.CharField(
        max_length=30,
        choices=[
            ('EQUAL', 'Equal Distribution'),
            ('PROPORTIONAL', 'Proportional to Contributions'),
            ('ROTATING', 'Rotating (Merry-Go-Round)'),
        ],
        help_text=_("Method used for distribution.")
    )

    class Meta:
        verbose_name = _('Payout')
        verbose_name_plural = _('Payouts')
        ordering = ['-payout_date']

    def __str__(self):
        return f"{self.chama.name} - Payout {self.payout_date}"


class PayoutRecipient(BaseModel):

    payout = models.ForeignKey(
        Payout,
        on_delete=models.CASCADE,
        related_name='recipients',
        help_text=_("The payout.")
    )

    member = models.ForeignKey(
        ChamaMember,
        on_delete=models.CASCADE,
        related_name='payouts_received',
        help_text=_("The member receiving the payout.")
    )

    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[validate_positive_amount],
        help_text=_("Amount received by this member.")
    )

    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text=_("Payment reference for the payout.")
    )

    class Meta:
        verbose_name = _('Payout Recipient')
        verbose_name_plural = _('Payout Recipients')
        unique_together = ['payout', 'member']

    def __str__(self):
        return f"{self.member.user.get_full_name()} - KSh {self.amount}"


class Poll(BaseModel):

    chama = models.ForeignKey(
        Chama, on_delete=models.CASCADE, related_name='polls'
    )

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True, default='')

    created_by = models.ForeignKey(
        ChamaMember, on_delete=models.CASCADE, related_name='created_polls'
    )

    voting_method = models.CharField(
        max_length=20,
        choices=[
            ('MAJORITY', 'Simple Majority'),
            ('TWO_THIRDS', 'Two-Thirds Majority'),
            ('UNANIMOUS', 'Unanimous'),
        ],
        default='MAJORITY',
    )

    is_anonymous = models.BooleanField(
        default=False,
        help_text=_("Whether votes are anonymous.")
    )

    is_active = models.BooleanField(default=True, db_index=True)

    closes_at = models.DateTimeField(null=True, blank=True)

    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Poll')
        verbose_name_plural = _('Polls')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.chama.name} - {self.title}"

    def close(self):
        self.is_active = False
        self.closed_at = timezone.now()
        self.save(update_fields=['is_active', 'closed_at'])

    def get_results(self):
        options = self.options.all()
        total_votes = sum(opt.votes.count() for opt in options)

        results = []
        for opt in options:
            vote_count = opt.votes.count()
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
            results.append({
                'option_id': str(opt.id),
                'option_text': opt.option_text,
                'votes': vote_count,
                'percentage': round(percentage, 1),
            })

        return {
            'total_votes': total_votes,
            'options': results,
            'passed': self._check_passed(results),
        }

    def _check_passed(self, results):
        if not results:
            return False

        total = sum(r['votes'] for r in results)
        if total == 0:
            return False

        winning = max(results, key=lambda r: r['votes'])
        winning_pct = winning['percentage']

        if self.voting_method == 'MAJORITY':
            return winning_pct > 50
        elif self.voting_method == 'TWO_THIRDS':
            return winning_pct >= 66.7
        elif self.voting_method == 'UNANIMOUS':
            return winning_pct == 100

        return False


class PollOption(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.poll.title} - {self.option_text}"


class Vote(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='all_votes')
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(
        ChamaMember, on_delete=models.CASCADE, related_name='votes_cast'
    )
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['poll', 'voter']

    def __str__(self):
        return f"{self.voter.user.get_full_name()} voted on {self.poll.title}"