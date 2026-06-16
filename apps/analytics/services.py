import logging
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Q, Sum
from django.utils import timezone

from apps.analytics.models import ChamaAnalytics, PlatformMetric, SACCOMarketAnalytics

logger = logging.getLogger(__name__)


class AnalyticsAggregationService:
    @classmethod
    def aggregate_platform_metrics(cls, target_date=None):
        if target_date is None:
            target_date = timezone.now().date()

        from apps.chamas.models import Chama, ChamaMember, Contribution, Loan
        from apps.investments.models import Connection, LiquidityRequest
        from apps.transactions.models import SettlementIntent, SettlementState
        from apps.users.models import User

        total_users = User.objects.filter(is_active=True).count()
        new_users = User.objects.filter(
            date_joined__date=target_date
        ).count()
        verified_users = User.objects.filter(
            id_verification_status='VERIFIED'
        ).count()
        active_users = User.objects.filter(
            last_login__date=target_date
        ).count()

        total_chamas = Chama.objects.filter(
            status='ACTIVE', is_deleted=False
        ).count()
        new_chamas = Chama.objects.filter(
            created_at__date=target_date, is_deleted=False
        ).count()
        total_chama_members = ChamaMember.objects.filter(
            is_active=True
        ).count()

        savings = Contribution.objects.filter(
            status='PAID'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        loans = Loan.objects.filter(
            status__in=['DISBURSED', 'PARTIALLY_REPAID']
        ).aggregate(total=Sum('outstanding_balance'))['total'] or Decimal('0')

        total_lr = LiquidityRequest.objects.filter(is_deleted=False).count()
        active_lr = LiquidityRequest.objects.filter(
            status='ACTIVE', is_deleted=False
        ).count()
        total_conn = Connection.objects.filter(is_deleted=False).count()

        settlements = SettlementIntent.objects.filter(is_deleted=False)
        total_settle = settlements.count()
        completed = settlements.filter(state=SettlementState.LEDGER_FINALIZED).count()
        reversed_settle = settlements.filter(state=SettlementState.REVERSED).count()
        disputed = settlements.filter(state=SettlementState.DISPUTED_MANUAL).count()

        volume = settlements.filter(
            state=SettlementState.LEDGER_FINALIZED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        fees = settlements.filter(
            state=SettlementState.LEDGER_FINALIZED
        ).aggregate(total=Sum('platform_fee'))['total'] or Decimal('0')

        from apps.investments.models import SACCO
        total_saccos = SACCO.objects.filter(status='ACTIVE', is_deleted=False).count()

        metric, created = PlatformMetric.objects.update_or_create(
            metric_date=target_date,
            defaults={
                'total_users': total_users,
                'new_users': new_users,
                'verified_users': verified_users,
                'active_users': active_users,
                'total_chamas': total_chamas,
                'new_chamas': new_chamas,
                'total_chama_members': total_chama_members,
                'total_chama_savings': savings,
                'total_chama_loans': loans,
                'total_liquidity_requests': total_lr,
                'active_liquidity_requests': active_lr,
                'total_connections': total_conn,
                'total_settlements': total_settle,
                'completed_settlements': completed,
                'reversed_settlements': reversed_settle,
                'disputed_settlements': disputed,
                'total_settlement_volume': volume,
                'total_platform_fees': fees,
                'total_saccos': total_saccos,
            }
        )

        logger.info(f"Platform metrics aggregated for {target_date}")
        return metric

    @classmethod
    def aggregate_chama_analytics(cls, chama, period_start, period_end, period_type='MONTHLY'):
        members = chama.memberships.filter(is_active=True)
        contributions = chama.contributions.filter(
            period_start__gte=period_start,
            period_end__lte=period_end
        )
        loans = chama.loans.filter(
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )
        meetings = chama.meetings.filter(
            date__gte=period_start,
            date__lte=period_end
        )

        total_contributions = contributions.filter(
            status='PAID'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        contribution_count = contributions.filter(status='PAID').count()
        avg_contribution = (
            total_contributions / contribution_count
            if contribution_count > 0 else Decimal('0')
        )

        total_contributions_all = contributions.count()
        on_time = contributions.filter(status='PAID').count()
        on_time_rate = (
            (Decimal(on_time) / Decimal(total_contributions_all) * 100)
            if total_contributions_all > 0 else Decimal('0')
        )

        analytics, created = ChamaAnalytics.objects.update_or_create(
            chama=chama,
            period_start=period_start,
            period_end=period_end,
            defaults={
                'period_type': period_type,
                'total_members': members.count(),
                'active_members': members.filter(
                    last_contribution_date__gte=period_start
                ).count(),
                'total_contributions': total_contributions,
                'average_contribution': avg_contribution.quantize(Decimal('0.01')),
                'on_time_rate': on_time_rate.quantize(Decimal('0.01')),
                'late_contributions': contributions.filter(status='LATE').count(),
                'missed_contributions': contributions.filter(status='MISSED').count(),
                'total_loans_issued': loans.count(),
                'total_loan_amount': loans.aggregate(
                    total=Sum('principal')
                )['total'] or Decimal('0'),
                'total_interest_earned': loans.filter(
                    status='FULLY_REPAID'
                ).aggregate(total=Sum('total_interest'))['total'] or Decimal('0'),
                'total_meetings': meetings.count(),
            }
        )

        return analytics

    @classmethod
    def aggregate_sacco_market_analytics(cls, sacco, target_date=None):
        if target_date is None:
            target_date = timezone.now().date()

        from apps.investments.models import LiquidityRequest
        from apps.transactions.models import SettlementIntent, SettlementState

        completed = SettlementIntent.objects.filter(
            seller_sacco_id=sacco.id,
            state=SettlementState.LEDGER_FINALIZED,
            finalized_at__date=target_date,
            is_deleted=False
        )

        transactions = completed.count()
        volume_shares = completed.aggregate(
            total=Sum('share_quantity')
        )['total'] or Decimal('0')
        volume_amount = completed.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')

        prices = completed.values_list('price_per_share', flat=True)
        if prices:
            avg_price = sum(prices) / len(prices)
            highest_price = max(prices)
            lowest_price = min(prices)
        else:
            avg_price = highest_price = lowest_price = None

        analytics, created = SACCOMarketAnalytics.objects.update_or_create(
            sacco=sacco,
            metric_date=target_date,
            defaults={
                'average_price_per_share': avg_price,
                'highest_price': highest_price,
                'lowest_price': lowest_price,
                'total_volume_shares': volume_shares,
                'total_volume_amount': volume_amount,
                'number_of_transactions': transactions,
                'active_sellers': LiquidityRequest.objects.filter(
                    sacco=sacco, status='ACTIVE', is_deleted=False
                ).count(),
            }
        )

        return analytics


class DashboardService:

    CACHE_TIMEOUT = 300  # 5 minutes

    @classmethod
    def get_platform_dashboard(cls):
        cache_key = 'dashboard:platform'
        data = cache.get(cache_key)

        if data is None:
            today = timezone.now().date()
            thirty_days_ago = today - timezone.timedelta(days=30)

            metrics = PlatformMetric.objects.filter(
                metric_date__gte=thirty_days_ago
            ).order_by('metric_date')

            data = {
                'summary': {
                    'total_users': metrics.last().total_users if metrics.exists() else 0,
                    'total_chamas': metrics.last().total_chamas if metrics.exists() else 0,
                    'total_savings': str(
                        metrics.last().total_chama_savings if metrics.exists() else 0
                    ),
                    'total_settlement_volume': str(
                        metrics.last().total_settlement_volume if metrics.exists() else 0
                    ),
                },
                'trends': {
                    'user_growth': [
                        {'date': str(m.metric_date), 'value': m.new_users}
                        for m in metrics
                    ],
                    'settlement_volume': [
                        {'date': str(m.metric_date), 'value': str(m.total_settlement_volume)}
                        for m in metrics
                    ],
                },
                'generated_at': str(timezone.now()),
            }

            cache.set(cache_key, data, cls.CACHE_TIMEOUT)

        return data

    @classmethod
    def get_user_dashboard(cls, user):
        cache_key = f'dashboard:user:{user.id}'
        data = cache.get(cache_key)

        if data is None:
            from apps.chamas.models import ChamaMember
            from apps.investments.models import (
                Connection,
                LiquidityRequest,
                SACCOMemberHolding,
            )
            from apps.notifications.services import NotificationService
            from apps.transactions.models import SettlementIntent

            memberships = ChamaMember.objects.filter(
                user=user, is_active=True
            ).select_related('chama')

            holdings = SACCOMemberHolding.objects.filter(
                user=user, verification_status='VERIFIED', is_deleted=False
            ).select_related('sacco')

            active_requests = LiquidityRequest.objects.filter(
                seller=user, status='ACTIVE', is_deleted=False
            ).count()

            connections = Connection.objects.filter(
                Q(seller=user) | Q(buyer=user),
                is_deleted=False
            ).exclude(status__in=['SETTLED', 'CLOSED']).count()

            recent_settlements = SettlementIntent.objects.filter(
                Q(buyer=user) | Q(seller=user),
                is_deleted=False
            ).order_by('-created_at')[:5]

            unread_count = NotificationService.get_unread_count(user)

            data = {
                'chamas': [
                    {
                        'id': str(m.chama.id),
                        'name': m.chama.name,
                        'role': m.get_role_display(),
                        'balance': str(m.current_balance),
                        'standing': str(m.standing_score),
                    }
                    for m in memberships
                ],
                'holdings': [
                    {
                        'id': str(h.id),
                        'sacco': h.sacco.name,
                        'shares': str(h.total_shares),
                        'available': str(h.available_shares),
                    }
                    for h in holdings
                ],
                'activity': {
                    'active_liquidity_requests': active_requests,
                    'active_connections': connections,
                },
                'recent_settlements': [
                    {
                        'id': str(s.uuid),
                        'state': s.get_state_display(),
                        'amount': str(s.amount),
                        'date': s.created_at.isoformat(),
                    }
                    for s in recent_settlements
                ],
                'unread_notifications': unread_count,
                'generated_at': str(timezone.now()),
            }

            cache.set(cache_key, data, 120)  # 2 minutes for user data

        return data

    @classmethod
    def invalidate_user_cache(cls, user):
        cache.delete(f'dashboard:user:{user.id}')

    @classmethod
    def invalidate_platform_cache(cls):
        cache.delete('dashboard:platform')