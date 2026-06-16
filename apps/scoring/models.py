import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class CreditScore(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='credit_scores'
    )

    chama = models.ForeignKey(
        'chamas.Chama', on_delete=models.CASCADE, related_name='member_scores'
    )

    score = models.PositiveIntegerField(
        default=300,
        help_text=_("Credit score (300-850).")
    )

    grade = models.CharField(
        max_length=3, blank=True, default='',
        help_text=_("Letter grade (A+, A, B, C, D, E).")
    )

    # Factor breakdown
    contribution_score = models.PositiveIntegerField(default=0)
    repayment_score = models.PositiveIntegerField(default=0)
    attendance_score = models.PositiveIntegerField(default=0)
    savings_score = models.PositiveIntegerField(default=0)
    trust_score = models.PositiveIntegerField(default=0)

    calculated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Credit Score')
        verbose_name_plural = _('Credit Scores')
        ordering = ['-calculated_at']
        indexes = [
            models.Index(fields=['user', 'chama', '-calculated_at']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.score} ({self.grade})"

    @classmethod
    def get_grade(cls, score):
        if score >= 800:
            return 'A+'
        elif score >= 750:
            return 'A'
        elif score >= 700:
            return 'B'
        elif score >= 600:
            return 'C'
        elif score >= 500:
            return 'D'
        else:
            return 'E'


class UnderwritingDecision(models.TextChoices):
    APPROVE = 'APPROVE', _('Approve')
    APPROVE_WITH_CONDITIONS = 'APPROVE_WITH_CONDITIONS', _('Approve with Conditions')
    FLAG_FOR_REVIEW = 'FLAG_FOR_REVIEW', _('Flag for Manual Review')
    REJECT = 'REJECT', _('Reject')


class LoanUnderwriting(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    loan = models.OneToOneField(
        'chamas.Loan', on_delete=models.CASCADE, related_name='underwriting'
    )

    credit_score = models.ForeignKey(
        CreditScore, on_delete=models.SET_NULL, null=True, blank=True
    )

    credit_score_value = models.PositiveIntegerField(default=0)

    chama_health_score = models.DecimalField(
        max_digits=4, decimal_places=1, default=0.0
    )

    decision = models.CharField(
        max_length=30, choices=UnderwritingDecision.choices,
        default=UnderwritingDecision.FLAG_FOR_REVIEW,
    )

    confidence_score = models.PositiveIntegerField(
        default=50, help_text=_("Confidence in the automated decision (0-100).")
    )

    reasoning = models.JSONField(
        default=list,
        help_text=_("List of factors contributing to the decision.")
    )

    conditions = models.JSONField(
        default=list,
        help_text=_("Conditions for approval if APPROVE_WITH_CONDITIONS.")
    )

    overridden_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='overridden_underwritings'
    )

    overridden_decision = models.CharField(
        max_length=30, choices=UnderwritingDecision.choices, null=True, blank=True
    )

    overridden_at = models.DateTimeField(null=True, blank=True)
    override_reason = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Loan Underwriting')
        verbose_name_plural = _('Loan Underwritings')
        ordering = ['-created_at']

    def __str__(self):
        return f"Underwriting for loan {self.loan.id}: {self.decision}"