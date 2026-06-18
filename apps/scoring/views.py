from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.scoring.services import CreditScoringService
from apps.scoring.models import CreditScore


class MyCreditScoreView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Scoring'],
        summary='Get my credit score',
        description='View your current credit score and breakdown.'
    )
    def get(self, request):
        chama_id = request.query_params.get('chama_id')

        scores = CreditScore.objects.filter(user=request.user)
        if chama_id:
            scores = scores.filter(chama_id=chama_id)

        latest = scores.order_by('-calculated_at').first()

        if not latest:
            return Response({
                'success': True,
                'data': {'has_score': False, 'message': 'No credit score available yet.'},
            })

        # Get history for trend
        history = scores.order_by('-calculated_at')[:6].values(
            'score', 'grade', 'calculated_at'
        )

        return Response({
            'success': True,
            'data': {
                'has_score': True,
                'score': latest.score,
                'grade': latest.grade,
                'breakdown': {
                    'contribution': latest.contribution_score,
                    'repayment': latest.repayment_score,
                    'attendance': latest.attendance_score,
                    'savings': latest.savings_score,
                    'trust': latest.trust_score,
                },
                'max_score': CreditScoringService.MAX_SCORE,
                'chama_name': latest.chama.name,
                'calculated_at': latest.calculated_at.isoformat(),
                'history': list(history),
            },
        })

class UnderwritingView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Scoring'],
        summary='Get underwriting decision',
        description='View the underwriting decision for a loan.'
    )
    def get(self, request, loan_id):
        from apps.scoring.models import LoanUnderwriting

        try:
            underwriting = LoanUnderwriting.objects.get(loan_id=loan_id)
        except LoanUnderwriting.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Underwriting not available.')}
            }, status=404)

        # Check user has permission
        loan = underwriting.loan
        is_borrower = loan.borrower.user == request.user
        is_chama_member = loan.chama.memberships.filter(
            user=request.user, is_active=True
        ).exists()

        if not is_borrower and not is_chama_member:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': _('Not authorized.')}
            }, status=403)

        return Response({
            'success': True,
            'data': {
                'decision': underwriting.decision,
                'confidence': underwriting.confidence_score,
                'reasoning': underwriting.reasoning,
                'conditions': underwriting.conditions,
                'credit_score': underwriting.credit_score_value,
                'chama_health': str(underwriting.chama_health_score),
                'overridden': bool(underwriting.overridden_by),
                'overridden_decision': underwriting.overridden_decision,
            },
        })


class OverrideUnderwritingView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Scoring'],
        summary='Override underwriting',
        description='Chama admin can override automated underwriting.'
    )
    def post(self, request, loan_id):
        from apps.scoring.models import LoanUnderwriting, UnderwritingDecision
        from apps.chamas.models import ChamaMember, MemberRole

        try:
            underwriting = LoanUnderwriting.objects.get(loan_id=loan_id)
        except LoanUnderwriting.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Underwriting not found.')}
            }, status=404)

        # Check admin
        chama = underwriting.loan.chama
        is_admin = ChamaMember.objects.filter(
            chama=chama, user=request.user, is_active=True,
            role__in=[MemberRole.CHAIRPERSON, MemberRole.TREASURER, MemberRole.SECRETARY],
        ).exists()

        if not is_admin:
            return Response({
                'success': False,
                'error': {'code': 'permission_denied', 'message': _('Only chama admins can override.')}
            }, status=403)

        new_decision = request.data.get('decision')
        reason = request.data.get('reason', '')

        if new_decision not in dict(UnderwritingDecision.choices):
            return Response({
                'success': False,
                'error': {'code': 'invalid_decision', 'message': _('Invalid decision.')}
            }, status=400)

        underwriting.overridden_by = request.user
        underwriting.overridden_decision = new_decision
        underwriting.overridden_at = timezone.now()
        underwriting.override_reason = reason
        underwriting.save()

        return Response({
            'success': True,
            'data': {
                'original_decision': underwriting.decision,
                'new_decision': new_decision,
            },
            'message': _('Underwriting decision overridden.'),
        })