from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext_lazy as _

from apps.analytics.services import DashboardService, AnalyticsAggregationService
from apps.analytics.models import (
    PlatformMetric, ChamaAnalytics, SACCOMarketAnalytics,
    ScheduledReport, ReportGeneration
)
from apps.analytics.serializers import (
    PlatformMetricSerializer, ChamaAnalyticsSerializer,
    SACCOMarketAnalyticsSerializer, ScheduledReportSerializer,
    ReportGenerationSerializer,
)
from apps.users.permissions import IsPlatformStaff


class PlatformDashboardView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Analytics'], summary='Get platform dashboard data')
    def get(self, request):
        data = DashboardService.get_platform_dashboard()
        return Response({'success': True, 'data': data})


class UserDashboardView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Analytics'], summary='Get user dashboard data')
    def get(self, request):
        data = DashboardService.get_user_dashboard(request.user)
        return Response({'success': True, 'data': data})


class ChamaAnalyticsView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Analytics'], summary='Get chama analytics')
    def get(self, request, chama_id):
        from django.utils import timezone

        period = request.query_params.get('period', 'MONTHLY')
        today = timezone.now().date()

        if period == 'WEEKLY':
            start = today - timezone.timedelta(days=7)
        elif period == 'MONTHLY':
            start = today - timezone.timedelta(days=30)
        elif period == 'QUARTERLY':
            start = today - timezone.timedelta(days=90)
        else:
            start = today - timezone.timedelta(days=365)

        from apps.chamas.models import Chama
        try:
            chama = Chama.objects.get(id=chama_id)
        except Chama.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('Chama not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        if not chama.memberships.filter(user=request.user, is_active=True).exists():
            return Response({
                'success': False,
                'error': {'code': 'not_member', 'message': _('Not a member.')}
            }, status=status.HTTP_403_FORBIDDEN)

        analytics = AnalyticsAggregationService.aggregate_chama_analytics(
            chama, start, today, period
        )

        return Response({
            'success': True,
            'data': ChamaAnalyticsSerializer(analytics).data,
        })


class SACCOMarketView(APIView):

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Analytics'], summary='Get SACCO market analytics')
    def get(self, request, sacco_id):
        from django.utils import timezone
        from apps.investments.models import SACCO

        try:
            sacco = SACCO.objects.get(id=sacco_id)
        except SACCO.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'not_found', 'message': _('SACCO not found.')}
            }, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)

        analytics = SACCOMarketAnalytics.objects.filter(
            sacco=sacco,
            metric_date__gte=start_date
        ).order_by('metric_date')

        return Response({
            'success': True,
            'data': SACCOMarketAnalyticsSerializer(analytics, many=True).data,
        })


class RefreshAnalyticsView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Analytics'], summary='Refresh platform analytics')
    def post(self, request):
        target_date = request.data.get('date')
        if target_date:
            from datetime import datetime
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

        metric = AnalyticsAggregationService.aggregate_platform_metrics(target_date)
        DashboardService.invalidate_platform_cache()

        return Response({
            'success': True,
            'data': PlatformMetricSerializer(metric).data,
            'message': _('Analytics refreshed.'),
        })