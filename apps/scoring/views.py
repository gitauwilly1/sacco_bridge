from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

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