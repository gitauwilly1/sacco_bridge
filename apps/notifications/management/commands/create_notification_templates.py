from django.core.management.base import BaseCommand
from apps.notifications.models import (
    NotificationTemplate, NotificationCategory,
    NotificationPriority, NotificationChannel
)


class Command(BaseCommand):
    help = 'Creates default notification templates for Sacco Bridge'

    TEMPLATES = [
        # Chama Contribution Templates
        {
            'name': 'chama_contribution_received',
            'category': NotificationCategory.CHAMA_CONTRIBUTION,
            'title_template': 'Contribution Received',
            'body_template': 'Your contribution of KSh {amount} to {chama_name} has been received.',
            'sms_template': 'KSh {amount} contribution to {chama_name} confirmed.',
            'email_subject_template': 'Contribution Confirmed - {chama_name}',
            'email_body_template': '<p>Your contribution of <strong>KSh {amount}</strong> to <strong>{chama_name}</strong> has been received.</p>',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.MEDIUM,
        },
        {
            'name': 'chama_contribution_reminder',
            'category': NotificationCategory.CHAMA_CONTRIBUTION,
            'title_template': 'Contribution Reminder',
            'body_template': 'Your contribution of KSh {amount} to {chama_name} is due by {due_date}.',
            'sms_template': 'Reminder: KSh {amount} contribution to {chama_name} due by {due_date}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.HIGH,
        },
        {
            'name': 'chama_contribution_overdue',
            'category': NotificationCategory.CHAMA_CONTRIBUTION,
            'title_template': 'Contribution Overdue',
            'body_template': 'Your contribution to {chama_name} is overdue. Late fee of KSh {late_fee} may apply.',
            'sms_template': 'Your {chama_name} contribution is overdue. Late fee may apply.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },

        # Chama Loan Templates
        {
            'name': 'loan_request_submitted',
            'category': NotificationCategory.CHAMA_LOAN,
            'title_template': 'Loan Request Submitted',
            'body_template': 'Your loan request for KSh {amount} from {chama_name} has been submitted for review.',
            'sms_template': 'Loan request for KSh {amount} submitted to {chama_name}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.MEDIUM,
        },
        {
            'name': 'loan_approved',
            'category': NotificationCategory.CHAMA_LOAN,
            'title_template': 'Loan Approved',
            'body_template': 'Your loan of KSh {amount} from {chama_name} has been approved.',
            'sms_template': 'Loan of KSh {amount} approved by {chama_name}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.HIGH,
        },
        {
            'name': 'loan_repayment_due',
            'category': NotificationCategory.CHAMA_LOAN,
            'title_template': 'Loan Repayment Due',
            'body_template': 'Your loan repayment of KSh {amount} to {chama_name} is due on {due_date}.',
            'sms_template': 'Loan repayment KSh {amount} due {due_date}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.HIGH,
        },

        # Investment Templates
        {
            'name': 'buyer_interest_received',
            'category': NotificationCategory.INVESTMENT_CONNECTION,
            'title_template': 'Buyer Interested in Your Shares',
            'body_template': '{buyer_name} is interested in purchasing your {share_quantity} shares in {sacco_name}.',
            'sms_template': '{buyer_name} wants to buy your {sacco_name} shares.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.HIGH,
        },
        {
            'name': 'offer_received',
            'category': NotificationCategory.INVESTMENT_OFFER,
            'title_template': 'New Offer Received',
            'body_template': '{offeror_name} offered KSh {price_per_share}/share for {quantity} shares in {sacco_name}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.HIGH,
        },
        {
            'name': 'offer_accepted',
            'category': NotificationCategory.INVESTMENT_OFFER,
            'title_template': 'Offer Accepted',
            'body_template': 'Your offer for {quantity} shares in {sacco_name} has been accepted. Settlement will begin shortly.',
            'sms_template': 'Your offer accepted. Settlement starting.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },

        # Settlement Templates
        {
            'name': 'settlement_initiated',
            'category': NotificationCategory.SETTLEMENT,
            'title_template': 'Settlement Initiated',
            'body_template': 'Settlement for {quantity} shares in {sacco_name} (KSh {amount}) has been initiated.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.MEDIUM,
        },
        {
            'name': 'settlement_completed',
            'category': NotificationCategory.SETTLEMENT,
            'title_template': 'Settlement Complete',
            'body_template': 'Transaction complete: {quantity} shares in {sacco_name} transferred. Amount: KSh {amount}.',
            'sms_template': 'Transaction complete: {quantity} {sacco_name} shares. KSh {amount}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },
        {
            'name': 'settlement_disputed',
            'category': NotificationCategory.DISPUTE,
            'title_template': 'Transaction Under Review',
            'body_template': 'Your transaction #{reference} requires additional review. Our team is investigating.',
            'sms_template': 'Transaction #{reference} under review. We will update you.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },
        {
            'name': 'settlement_reversed',
            'category': NotificationCategory.SETTLEMENT,
            'title_template': 'Transaction Reversed',
            'body_template': 'Transaction #{reference} has been reversed. KSh {amount} returned.',
            'sms_template': 'Transaction #{reference} reversed. KSh {amount} returned.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },

        # Security Templates
        {
            'name': 'login_alert',
            'category': NotificationCategory.SECURITY,
            'title_template': 'New Login Detected',
            'body_template': 'A new login was detected from {device} at {location}. If this was not you, secure your account.',
            'sms_template': 'New login from {device}. Not you? Secure your account.',
            'default_channels': [NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write('Creating notification templates...')

        created_count = 0
        for template_data in self.TEMPLATES:
            template, created = NotificationTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {template.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} new notification templates.'
            )
        )