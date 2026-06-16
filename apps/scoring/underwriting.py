import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class UnderwritingService:

    @classmethod
    def evaluate_loan(cls, loan):
        from apps.scoring.models import (
            CreditScore, LoanUnderwriting, UnderwritingDecision,
        )
        from apps.chamas.models import LoanStatus

        reasoning = []
        conditions = []
        decision = UnderwritingDecision.FLAG_FOR_REVIEW
        confidence = 50

        borrower = loan.borrower
        chama = loan.chama
        credit_score = None
        credit_score_value = 0

        # Get latest credit score
        credit_score = CreditScore.objects.filter(
            user=borrower.user, chama=chama
        ).order_by('-calculated_at').first()

        if credit_score:
            credit_score_value = credit_score.score

        # Get chama health
        chama_health = chama.health_score or Decimal('0')

        # ---- REJECTION CHECKS ----

        # Check for active defaults
        from apps.chamas.models import Loan
        active_defaults = Loan.objects.filter(
            borrower=borrower,
            status=LoanStatus.DEFAULTED,
            is_deleted=False,
        ).exists()

        if active_defaults:
            reasoning.append("Borrower has active defaulted loans.")
            decision = UnderwritingDecision.REJECT
            confidence = 95
            return cls._create_decision(
                loan, credit_score, credit_score_value, chama_health,
                decision, confidence, reasoning, conditions
            )

        # Chama health rejection
        if chama_health < Decimal('30'):
            reasoning.append(f"Chama health score ({chama_health}) is critically low.")
            decision = UnderwritingDecision.REJECT
            confidence = 90
            return cls._create_decision(
                loan, credit_score, credit_score_value, chama_health,
                decision, confidence, reasoning, conditions
            )

        # Credit score rejection
        if credit_score_value < 500:
            reasoning.append(f"Credit score ({credit_score_value}) is below minimum threshold (500).")
            decision = UnderwritingDecision.REJECT
            confidence = 85
            return cls._create_decision(
                loan, credit_score, credit_score_value, chama_health,
                decision, confidence, reasoning, conditions
            )

        # ---- APPROVAL CHECKS ----

        max_loan = borrower.total_contributions * chama.max_loan_multiple
        requested_multiple = loan.principal / borrower.total_contributions if borrower.total_contributions > 0 else 999

        # High credit score approvals
        if credit_score_value >= 800:
            if requested_multiple <= 3:
                reasoning.append(f"Excellent credit score ({credit_score_value}).")
                reasoning.append(f"Requested amount within standard limits ({requested_multiple:.1f}x contributions).")
                decision = UnderwritingDecision.APPROVE
                confidence = 90
            elif requested_multiple <= 4:
                reasoning.append(f"Excellent credit score ({credit_score_value}).")
                reasoning.append(f"Requested amount slightly above standard ({requested_multiple:.1f}x).")
                conditions.append("Repayment within reduced duration recommended.")
                decision = UnderwritingDecision.APPROVE_WITH_CONDITIONS
                confidence = 75

        elif credit_score_value >= 700:
            if requested_multiple <= 2:
                reasoning.append(f"Good credit score ({credit_score_value}).")
                decision = UnderwritingDecision.APPROVE
                confidence = 80
            elif requested_multiple <= 3:
                reasoning.append(f"Good credit score ({credit_score_value}) but higher multiple ({requested_multiple:.1f}x).")
                decision = UnderwritingDecision.FLAG_FOR_REVIEW
                confidence = 60

        elif credit_score_value >= 600:
            if requested_multiple <= 1.5:
                reasoning.append(f"Fair credit score ({credit_score_value}).")
                decision = UnderwritingDecision.APPROVE
                confidence = 65
            else:
                reasoning.append(f"Fair credit score ({credit_score_value}) with higher multiple ({requested_multiple:.1f}x).")
                decision = UnderwritingDecision.FLAG_FOR_REVIEW
                confidence = 50

        else:  # 500-599
            reasoning.append(f"Low credit score ({credit_score_value}). Manual review recommended.")
            decision = UnderwritingDecision.FLAG_FOR_REVIEW
            confidence = 40

        # First loan adjustment
        previous_loans = Loan.objects.filter(
            borrower=borrower,
            is_deleted=False,
        ).exclude(id=loan.id).count()

        if previous_loans == 0:
            reasoning.append("First loan application - increased scrutiny.")
            if decision == UnderwritingDecision.APPROVE:
                decision = UnderwritingDecision.APPROVE_WITH_CONDITIONS
                conditions.append("Maximum 1x contributions for first loan.")
                conditions.append("Shorter repayment period recommended (3 months max).")
            confidence = max(confidence - 15, 30)

        return cls._create_decision(
            loan, credit_score, credit_score_value, chama_health,
            decision, confidence, reasoning, conditions
        )

    @classmethod
    def _create_decision(cls, loan, credit_score, credit_score_value,
                         chama_health, decision, confidence, reasoning, conditions):
        from apps.scoring.models import LoanUnderwriting

        underwriting = LoanUnderwriting.objects.create(
            loan=loan,
            credit_score=credit_score,
            credit_score_value=credit_score_value,
            chama_health_score=chama_health,
            decision=decision,
            confidence_score=confidence,
            reasoning=reasoning,
            conditions=conditions,
        )

        logger.info(
            f"Underwriting for loan {loan.id}: {decision} "
            f"(confidence={confidence}%, score={credit_score_value})"
        )

        return underwriting