from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.models import NotificationDelivery, DeliveryStatus


class Command(BaseCommand):
    help = 'Show dead-letter queue status for notification deliveries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Show failures from last N days (default: 7)'
        )
        parser.add_argument(
            '--replay',
            type=str,
            nargs='*',
            help='Replay specific delivery IDs'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff = timezone.now() - timezone.timedelta(days=days)

        # Find permanently failed deliveries
        failed = NotificationDelivery.objects.filter(
            status=DeliveryStatus.FAILED,
            sent_at__gte=cutoff,
            retry_count__gte=3,
        ).select_related('notification__user')

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  DEAD-LETTER QUEUE STATUS")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"  Period: Last {days} days")
        self.stdout.write(f"  Total failed: {failed.count()}")
        self.stdout.write(f"{'='*60}\n")

        if failed.exists():
            for delivery in failed.order_by('-sent_at')[:20]:
                self.stdout.write(
                    f"  ID: {delivery.id} | "
                    f"Channel: {delivery.get_channel_display()} | "
                    f"User: {delivery.notification.user.email} | "
                    f"Error: {delivery.error_message[:80]} | "
                    f"Retries: {delivery.retry_count} | "
                    f"Date: {delivery.sent_at.strftime('%Y-%m-%d %H:%M')}"
                )

        # Show stale pending deliveries
        stale = NotificationDelivery.objects.filter(
            status=DeliveryStatus.PENDING,
            notification__created_at__lt=timezone.now() - timezone.timedelta(hours=1),
        )

        if stale.exists():
            self.stdout.write(f"\n  STALE PENDING ({stale.count()}):")
            for delivery in stale[:10]:
                self.stdout.write(
                    f"  ID: {delivery.id} | "
                    f"Channel: {delivery.get_channel_display()} | "
                    f"Age: {(timezone.now() - delivery.notification.created_at).total_seconds() / 3600:.1f}h"
                )

        # Replay if requested
        replay_ids = options.get('replay', [])
        if replay_ids:
            from apps.notifications.tasks import (
                deliver_push, deliver_sms, deliver_email
            )
            for did in replay_ids:
                try:
                    delivery = NotificationDelivery.objects.get(id=did)
                    delivery.status = DeliveryStatus.PENDING
                    delivery.retry_count = 0
                    delivery.save()

                    if delivery.channel == 'PUSH':
                        deliver_push.delay(delivery.id)
                    elif delivery.channel == 'SMS':
                        deliver_sms.delay(delivery.id)
                    elif delivery.channel == 'EMAIL':
                        deliver_email.delay(delivery.id)

                    self.stdout.write(
                        self.style.SUCCESS(f"  Replayed delivery {did}")
                    )
                except NotificationDelivery.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"  Delivery {did} not found")
                    )

        self.stdout.write(f"\n{'='*60}\n")