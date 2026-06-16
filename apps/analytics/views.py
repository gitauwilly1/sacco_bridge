from decimal import Decimal

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import SACCOMarketAnalytics
from apps.analytics.serializers import (
    ChamaAnalyticsSerializer,
    PlatformMetricSerializer,
    SACCOMarketAnalyticsSerializer,
)
from apps.analytics.services import AnalyticsAggregationService, DashboardService
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

class AdminAnalyticsView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Admin'], summary='[Admin] Platform overview stats')
    def get(self, request):
        from django.db.models import Sum

        from apps.chamas.models import Chama, Contribution, Loan
        from apps.investments.models import SACCO, LiquidityRequest
        from apps.mpesa.models import MpesaTransaction, MpesaTransactionStatus
        from apps.transactions.models import SettlementIntent, SettlementState
        from apps.users.models import User

        today = timezone.now().date()
        this_month = today.replace(day=1)
        last_month = (this_month - timezone.timedelta(days=1)).replace(day=1)

        # User stats
        total_users = User.objects.filter(is_active=True).count()
        new_users_month = User.objects.filter(date_joined__date__gte=this_month).count()
        verified_users = User.objects.filter(id_verification_status='VERIFIED').count()
        unverified_users = User.objects.filter(id_verification_status='UNVERIFIED').count()

        # Chama stats
        total_chamas = Chama.objects.filter(status='ACTIVE', is_deleted=False).count()
        total_chama_savings = Contribution.objects.filter(
            status='PAID'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_chama_loans = Loan.objects.filter(
            status__in=['DISBURSED', 'PARTIALLY_REPAID']
        ).aggregate(total=Sum('outstanding_balance'))['total'] or Decimal('0')

        # SACCO stats
        total_saccos = SACCO.objects.filter(status='ACTIVE', is_deleted=False).count()
        active_listings = LiquidityRequest.objects.filter(
            status='ACTIVE', is_deleted=False
        ).count()

        # Settlement stats
        settlements = SettlementIntent.objects.filter(is_deleted=False)
        total_settlements = settlements.count()
        completed = settlements.filter(state=SettlementState.LEDGER_FINALIZED).count()
        disputed = settlements.filter(state=SettlementState.DISPUTED_MANUAL).count()
        reversed_count = settlements.filter(state=SettlementState.REVERSED).count()

        total_volume = settlements.filter(
            state=SettlementState.LEDGER_FINALIZED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        total_fees = settlements.filter(
            state=SettlementState.LEDGER_FINALIZED
        ).aggregate(total=Sum('platform_fee'))['total'] or Decimal('0')

        # M-Pesa stats
        mpesa_transactions = MpesaTransaction.objects.filter(is_deleted=False)
        mpesa_completed = mpesa_transactions.filter(
            status=MpesaTransactionStatus.COMPLETED
        ).count()
        mpesa_volume = mpesa_transactions.filter(
            status=MpesaTransactionStatus.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Disputes
        open_disputes = settlements.filter(state=SettlementState.DISPUTED_MANUAL).count()

        return Response({
            'success': True,
            'data': {
                'users': {
                    'total': total_users,
                    'new_this_month': new_users_month,
                    'verified': verified_users,
                    'unverified': unverified_users,
                },
                'chamas': {
                    'total_active': total_chamas,
                    'total_savings': str(total_chama_savings),
                    'total_outstanding_loans': str(total_chama_loans),
                },
                'saccos': {
                    'total_active': total_saccos,
                    'active_liquidity_requests': active_listings,
                },
                'settlements': {
                    'total': total_settlements,
                    'completed': completed,
                    'disputed': disputed,
                    'reversed': reversed_count,
                    'total_volume': str(total_volume),
                    'total_fees_collected': str(total_fees),
                },
                'mpesa': {
                    'completed_transactions': mpesa_completed,
                    'total_volume': str(mpesa_volume),
                },
                'disputes': {
                    'open': open_disputes,
                },
                'generated_at': str(timezone.now()),
            }
        })


class AdminSettlementListView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Admin'], summary='[Admin] List all settlements')
    def get(self, request):
        from apps.core.pagination import SmallPagination
        from apps.transactions.models import SettlementIntent

        state_filter = request.query_params.get('state')
        settlements = SettlementIntent.objects.filter(is_deleted=False).order_by('-created_at')

        if state_filter:
            settlements = settlements.filter(state=state_filter)

        paginator = SmallPagination()
        page = paginator.paginate_queryset(settlements, request)

        data = []
        for s in page:
            data.append({
                'id': str(s.id),
                'uuid': str(s.uuid),
                'state': s.get_state_display(),
                'buyer': s.buyer.get_full_name(),
                'seller': s.seller.get_full_name(),
                'amount': str(s.amount),
                'sacco': s.seller_sacco_name,
                'created_at': s.created_at.isoformat(),
                'finalized_at': s.finalized_at.isoformat() if s.finalized_at else None,
            })

        return paginator.get_paginated_response(data)


class AdminTransactionVolumeView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Admin'], summary='[Admin] Transaction volume trends')
    def get(self, request):
        from django.db.models import Sum
        from django.db.models.functions import TruncDate

        from apps.transactions.models import SettlementIntent, SettlementState

        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)

        daily_volume = SettlementIntent.objects.filter(
            state=SettlementState.LEDGER_FINALIZED,
            finalized_at__date__gte=start_date,
            is_deleted=False
        ).annotate(
            date=TruncDate('finalized_at')
        ).values('date').annotate(
            total_volume=Sum('amount'),
            total_fees=Sum('platform_fee'),
            transaction_count=Count('id')
        ).order_by('date')

        return Response({
            'success': True,
            'data': [
                {
                    'date': str(item['date']),
                    'volume': str(item['total_volume'] or 0),
                    'fees': str(item['total_fees'] or 0),
                    'count': item['transaction_count'],
                }
                for item in daily_volume
            ]
        })


class AdminHealthCheckView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Admin'], summary='[Admin] System health check')
    def get(self, request):
        from django.core.cache import cache
        from django.db import connections
        from redis.exceptions import RedisError

        health = {
            'status': 'healthy',
            'timestamp': str(timezone.now()),
            'services': {}
        }

        # Database check
        try:
            db_conn = connections['default']
            db_conn.cursor()
            health['services']['database'] = {'status': 'up', 'engine': 'PostgreSQL'}
        except Exception as e:
            health['services']['database'] = {'status': 'down', 'error': str(e)}
            health['status'] = 'degraded'

        # Redis check
        try:
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            health['services']['redis'] = {'status': 'up' if result == 'ok' else 'degraded'}
        except RedisError as e:
            health['services']['redis'] = {'status': 'down', 'error': str(e)}
            health['status'] = 'degraded'

        # Celery check
        try:
            from sacco_bridge.celery import app
            inspector = app.control.inspect()
            stats = inspector.stats()
            if stats:
                health['services']['celery'] = {
                    'status': 'up',
                    'workers': len(stats),
                    'worker_names': list(stats.keys()),
                }
            else:
                health['services']['celery'] = {'status': 'down', 'error': 'No workers found'}
                if health['status'] == 'healthy':
                    health['status'] = 'degraded'
        except Exception as e:
            health['services']['celery'] = {'status': 'down', 'error': str(e)}
            if health['status'] == 'healthy':
                health['status'] = 'degraded'

        # Disk usage
        try:
            import shutil
            disk = shutil.disk_usage('/')
            health['services']['disk'] = {
                'status': 'up',
                'total_gb': round(disk.total / (1024**3), 1),
                'used_gb': round(disk.used / (1024**3), 1),
                'free_gb': round(disk.free / (1024**3), 1),
                'usage_percent': round((disk.used / disk.total) * 100, 1),
            }
        except Exception:
            health['services']['disk'] = {'status': 'unknown'}

        # App info
        health['app'] = {
            'version': '1.0.0',
            'environment': 'production' if not settings.DEBUG else 'development',
            'debug': settings.DEBUG,
            'python_version': '3.12',
            'django_version': '5.0',
        }

        status_code = 200 if health['status'] == 'healthy' else 503

        return Response({'success': True, 'data': health}, status=status_code)
    

class AdminExportCSVView(APIView):

    permission_classes = [permissions.IsAuthenticated, IsPlatformStaff]

    @extend_schema(tags=['Admin'], summary='[Admin] Export data as CSV')
    def get(self, request):
        pass

        export_type = request.query_params.get('type', 'users')
        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')

        if export_type == 'users':
            return self._export_users(date_from, date_to)
        elif export_type == 'chamas':
            return self._export_chamas(date_from, date_to)
        elif export_type == 'settlements':
            return self._export_settlements(date_from, date_to)
        elif export_type == 'transactions':
            return self._export_mpesa_transactions(date_from, date_to)
        else:
            return Response({
                'success': False,
                'error': {
                    'code': 'invalid_type',
                    'message': _('Invalid export type. Use: users, chamas, settlements, transactions.')
                }
            }, status=status.HTTP_400_BAD_REQUEST)

    def _export_users(self, date_from, date_to):
        import csv

        from django.http import HttpResponse

        from apps.users.models import User

        queryset = User.objects.filter(is_active=True).order_by('-date_joined')

        if date_from:
            queryset = queryset.filter(date_joined__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date_joined__date__lte=date_to)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sacco_bridge_users.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'User ID', 'Email', 'Phone', 'First Name', 'Last Name',
            'Email Verified', 'Phone Verified', 'ID Status',
            'Trust Score', 'Roles', 'Date Joined', 'Last Login'
        ])

        for user in queryset:
            writer.writerow([
                str(user.id),
                user.email,
                user.phone_number,
                user.first_name,
                user.last_name,
                'Yes' if user.email_verified else 'No',
                'Yes' if user.phone_verified else 'No',
                user.get_id_verification_status_display(),
                str(user.trust_score),
                ', '.join(user.user_roles.filter(is_active=True).values_list('role', flat=True)),
                user.date_joined.strftime('%Y-%m-%d %H:%M'),
                user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
            ])

        return response

    def _export_chamas(self, date_from, date_to):
        import csv

        from django.http import HttpResponse

        from apps.chamas.models import Chama

        queryset = Chama.objects.filter(is_deleted=False).order_by('-created_at')

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sacco_bridge_chamas.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Chama ID', 'Name', 'Type', 'Status', 'Members',
            'Total Savings (KSh)', 'Outstanding Loans (KSh)',
            'Contribution Amount', 'Frequency', 'Created'
        ])

        for chama in queryset:
            writer.writerow([
                str(chama.id),
                chama.name,
                chama.get_chama_type_display(),
                chama.status,
                chama.memberships.filter(is_active=True).count(),
                str(chama.total_savings),
                str(chama.outstanding_loans),
                str(chama.contribution_amount),
                chama.get_contribution_frequency_display(),
                chama.created_at.strftime('%Y-%m-%d'),
            ])

        return response

    def _export_settlements(self, date_from, date_to):
        import csv

        from django.http import HttpResponse

        from apps.transactions.models import SettlementIntent

        queryset = SettlementIntent.objects.filter(is_deleted=False).order_by('-created_at')

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sacco_bridge_settlements.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Settlement UUID', 'State', 'Buyer', 'Seller', 'SACCO',
            'Amount (KSh)', 'Shares', 'Price/Share', 'Platform Fee',
            'Created', 'Finalized'
        ])

        for s in queryset:
            writer.writerow([
                str(s.uuid),
                s.get_state_display(),
                s.buyer.get_full_name(),
                s.seller.get_full_name(),
                s.seller_sacco_name,
                str(s.amount),
                str(s.share_quantity),
                str(s.price_per_share),
                str(s.platform_fee),
                s.created_at.strftime('%Y-%m-%d %H:%M'),
                s.finalized_at.strftime('%Y-%m-%d %H:%M') if s.finalized_at else 'N/A',
            ])

        return response

    def _export_mpesa_transactions(self, date_from, date_to):
        import csv

        from django.http import HttpResponse

        from apps.mpesa.models import MpesaTransaction

        queryset = MpesaTransaction.objects.filter(is_deleted=False).order_by('-created_at')

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sacco_bridge_mpesa.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Transaction ID', 'Type', 'Status', 'Phone', 'Amount (KSh)',
            'Receipt', 'User', 'Initiated', 'Completed'
        ])

        for t in queryset:
            writer.writerow([
                str(t.transaction_id),
                t.get_transaction_type_display(),
                t.get_status_display(),
                t.phone_number,
                str(t.amount),
                t.mpesa_receipt_number or 'N/A',
                t.user.get_full_name(),
                t.initiated_at.strftime('%Y-%m-%d %H:%M') if t.initiated_at else 'N/A',
                t.completed_at.strftime('%Y-%m-%d %H:%M') if t.completed_at else 'N/A',
            ])

        return response