import logging
from celery import shared_task
from django.utils import timezone

from apps.analytics.services import AnalyticsAggregationService, DashboardService

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.analytics.tasks.aggregate_daily_platform_metrics',
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def aggregate_daily_platform_metrics(self):
    logger.info("Starting daily platform metrics aggregation...")

    try:
        today = timezone.now().date()
        metric = AnalyticsAggregationService.aggregate_platform_metrics(today)

        # Invalidate platform cache to force refresh
        DashboardService.invalidate_platform_cache()

        logger.info(f"Platform metrics aggregated for {today}")

        return {
            'date': str(today),
            'total_users': metric.total_users,
            'total_settlements': metric.total_settlements,
            'total_volume': str(metric.total_settlement_volume),
        }

    except Exception as e:
        logger.error(f"Platform metrics aggregation failed: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    name='apps.analytics.tasks.aggregate_weekly_chama_analytics',
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def aggregate_weekly_chama_analytics(self):
    logger.info("Starting weekly chama analytics aggregation...")

    from apps.chamas.models import Chama

    try:
        today = timezone.now().date()
        week_start = today - timezone.timedelta(days=7)

        chamas = Chama.objects.filter(status='ACTIVE', is_deleted=False)
        aggregated_count = 0

        for chama in chamas:
            try:
                AnalyticsAggregationService.aggregate_chama_analytics(
                    chama, week_start, today, 'WEEKLY'
                )
                aggregated_count += 1
            except Exception as e:
                logger.error(
                    f"Error aggregating analytics for chama {chama.id}: {str(e)}"
                )

        logger.info(
            f"Weekly chama analytics complete: {aggregated_count}/{chamas.count()} chamas"
        )

        return {
            'total_chamas': chamas.count(),
            'aggregated': aggregated_count,
        }

    except Exception as e:
        logger.error(f"Weekly chama analytics failed: {str(e)}")
        raise self.retry(exc=e)