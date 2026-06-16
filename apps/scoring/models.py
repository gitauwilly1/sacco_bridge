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