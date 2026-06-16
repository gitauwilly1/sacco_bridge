import logging

from django.core.management.base import BaseCommand

from apps.transactions.services import RecoveryService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scan for and attempt recovery of stuck settlements'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be recovered without making changes'
        )
        parser.add_argument(
            '--settlement-id',
            type=str,
            help='Attempt recovery for a specific settlement UUID'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        specific_id = options.get('settlement_id')

        if specific_id:
            from apps.transactions.models import SettlementIntent
            try:
                stuck = [SettlementIntent.objects.get(uuid=specific_id)]
            except SettlementIntent.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Settlement {specific_id} not found.'))
                return
        else:
            stuck = RecoveryService.find_stuck_settlements()

        self.stdout.write(f'Found {len(stuck)} stuck settlement(s).')

        for intent in stuck:
            self.stdout.write(
                f'  Settlement {intent.uuid}: {intent.get_state_display()} '
                f'(Retry {intent.retry_count}/{intent.max_retries})'
            )

            if dry_run:
                continue

            recovered = RecoveryService.attempt_recovery(intent)

            if recovered:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'    Recovery attempted for {intent.uuid}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'    Escalated {intent.uuid} to manual review'
                    )
                )

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run - no changes made.'))
        else:
            self.stdout.write(self.style.SUCCESS('Recovery scan complete.'))