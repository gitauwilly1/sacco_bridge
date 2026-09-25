"""Tests for CreditScoringService and LoanUnderwriting evaluation."""
from decimal import Decimal
import pytest
from apps.core.tests.factories import UserFactory, ChamaFactory, ChamaMemberFactory
from apps.scoring.services import CreditScoringService
from apps.scoring.models import CreditScore


@pytest.mark.django_db
class TestCreditScoringService:
    def test_calculate_score_new_member_defaults(self):
        user = UserFactory(email="new_member_score@test.com", phone_number="0755111222")
        chama = ChamaFactory(name="Score Test Chama")
        member = ChamaMemberFactory(user=user, chama=chama)

        result = CreditScoringService.calculate_score(user=user, chama=chama)
        assert result is not None
        score_value = result['score']
        assert isinstance(score_value, (int, float))
        assert score_value >= 0
        assert score_value <= 1000

    def test_credit_score_grade_mapping(self):
        assert CreditScore.get_grade(800) == "A+"
        assert CreditScore.get_grade(750) == "A"
        assert CreditScore.get_grade(700) == "B"
        assert CreditScore.get_grade(650) == "C"
        assert CreditScore.get_grade(500) == "D"
        assert CreditScore.get_grade(400) == "E"
