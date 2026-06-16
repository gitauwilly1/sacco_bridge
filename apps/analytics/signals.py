import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.analytics.services import DashboardService

logger = logging.getLogger(__name__)


@receiver(post_save, sender='chamas.Contribution')
def invalidate_on_contribution(sender, instance, created, **kwargs):
    try:
        if hasattr(instance, 'member') and instance.member:
            DashboardService.invalidate_user_cache(instance.member.user)
        DashboardService.invalidate_platform_cache()
    except Exception as e:
        logger.warning(f"Cache invalidation failed for contribution: {e}")


@receiver(post_save, sender='chamas.Loan')
def invalidate_on_loan(sender, instance, **kwargs):
    try:
        if hasattr(instance, 'borrower') and instance.borrower:
            DashboardService.invalidate_user_cache(instance.borrower.user)
        DashboardService.invalidate_platform_cache()
    except Exception as e:
        logger.warning(f"Cache invalidation failed for loan: {e}")


@receiver(post_save, sender='transactions.SettlementIntent')
def invalidate_on_settlement(sender, instance, **kwargs):
    try:
        if hasattr(instance, 'buyer'):
            DashboardService.invalidate_user_cache(instance.buyer)
        if hasattr(instance, 'seller'):
            DashboardService.invalidate_user_cache(instance.seller)
        DashboardService.invalidate_platform_cache()
    except Exception as e:
        logger.warning(f"Cache invalidation failed for settlement: {e}")


@receiver(post_save, sender='investments.LiquidityRequest')
def invalidate_on_liquidity_request(sender, instance, **kwargs):
    try:
        DashboardService.invalidate_platform_cache()
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")