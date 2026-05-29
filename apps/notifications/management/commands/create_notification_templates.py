from django.core.management.base import BaseCommand
from apps.notifications.models import (
    NotificationTemplate, NotificationCategory,
    NotificationPriority, NotificationChannel
)


class Command(BaseCommand):
    help = 'Creates default notification templates for all notification types'

    def handle(self, *args, **options):
        self.stdout.write('Creating default notification templates...')

        templates = [
            # Settlement notifications
            {
                'name': 'settlement_matched',
                'category': NotificationCategory.SETTLEMENT,
                'title_template': 'Settlement Matched',
                'body_template': 'Your {transaction_type} of {share_quantity} shares in {sacco_name} has been matched. Amount: KSh {amount}.',
                'sms_template': 'Sacco Bridge: Your {transaction_type} of {share_quantity} shares in {sacco_name} for KSh {amount} has been matched.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/settlements/{settlement_id}',
            },
            {
                'name': 'settlement_buyer_debited',
                'category': NotificationCategory.SETTLEMENT,
                'title_template': 'Payment Processed',
                'body_template': 'KSh {amount} has been debited from your account for the purchase of {share_quantity} shares in {sacco_name}.',
                'sms_template': 'Sacco Bridge: KSh {amount} debited for {share_quantity} shares in {sacco_name}. Ref: {reference_id}',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/settlements/{settlement_id}',
            },
            {
                'name': 'settlement_completed',
                'category': NotificationCategory.SETTLEMENT,
                'title_template': 'Transaction Complete',
                'body_template': 'Your {transaction_type} of {share_quantity} shares in {sacco_name} for KSh {amount} has been completed.',
                'sms_template': 'Sacco Bridge: Transaction complete. {transaction_type} of {share_quantity} shares in {sacco_name} for KSh {amount}. Ref: {reference_id}',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS, NotificationChannel.EMAIL],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/settlements/{settlement_id}',
            },
            {
                'name': 'settlement_disputed',
                'category': NotificationCategory.DISPUTE,
                'title_template': 'Transaction Under Review',
                'body_template': 'Your transaction for {share_quantity} shares in {sacco_name} is under review. Reference: {reference_id}. Our team is investigating.',
                'sms_template': 'Sacco Bridge: Your transaction {reference_id} is under review. We will update you within 4 hours.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.URGENT,
                'action_url_template': '/settlements/{settlement_id}',
            },
            {
                'name': 'settlement_reversed',
                'category': NotificationCategory.SETTLEMENT,
                'title_template': 'Transaction Reversed',
                'body_template': 'Your transaction for {share_quantity} shares in {sacco_name} has been reversed. KSh {amount} has been returned.',
                'sms_template': 'Sacco Bridge: Transaction reversed. KSh {amount} returned. Ref: {reference_id}',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/settlements/{settlement_id}',
            },
            # Chama contribution notifications
            {
                'name': 'chama_contribution_received',
                'category': NotificationCategory.CHAMA_CONTRIBUTION,
                'title_template': 'Contribution Received',
                'body_template': 'Your contribution of KSh {amount} to {chama_name} has been received.',
                'sms_template': 'Sacco Bridge: KSh {amount} contribution to {chama_name} received.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
                'default_priority': NotificationPriority.MEDIUM,
                'action_url_template': '/chamas/{chama_id}/contributions',
            },
            {
                'name': 'chama_contribution_reminder',
                'category': NotificationCategory.CHAMA_CONTRIBUTION,
                'title_template': 'Contribution Reminder',
                'body_template': 'Your contribution of KSh {amount} to {chama_name} is due {due_date}. Please make your payment.',
                'sms_template': 'Sacco Bridge: Reminder - KSh {amount} contribution to {chama_name} due {due_date}.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/chamas/{chama_id}',
            },
            {
                'name': 'chama_contribution_overdue',
                'category': NotificationCategory.CHAMA_CONTRIBUTION,
                'title_template': 'Contribution Overdue',
                'body_template': 'Your contribution of KSh {amount} to {chama_name} is overdue. Late fee of KSh {late_fee} may apply.',
                'sms_template': 'Sacco Bridge: Overdue - KSh {amount} contribution to {chama_name}. Late fee may apply.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.URGENT,
                'action_url_template': '/chamas/{chama_id}',
            },
            # Chama loan notifications
            {
                'name': 'chama_loan_requested',
                'category': NotificationCategory.CHAMA_LOAN,
                'title_template': 'Loan Request Submitted',
                'body_template': 'Your loan request for KSh {amount} from {chama_name} has been submitted and is pending review.',
                'sms_template': 'Sacco Bridge: Loan request for KSh {amount} submitted to {chama_name}.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
                'default_priority': NotificationPriority.MEDIUM,
                'action_url_template': '/chamas/{chama_id}/loans/{loan_id}',
            },
            {
                'name': 'chama_loan_approved',
                'category': NotificationCategory.CHAMA_LOAN,
                'title_template': 'Loan Approved',
                'body_template': 'Your loan of KSh {amount} from {chama_name} has been approved. Repay KSh {monthly_installment}/month for {duration} months.',
                'sms_template': 'Sacco Bridge: Loan of KSh {amount} approved. Repay KSh {monthly_installment}/month. Ref: {reference_id}',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/chamas/{chama_id}/loans/{loan_id}',
            },
            {
                'name': 'chama_loan_disbursed',
                'category': NotificationCategory.CHAMA_LOAN,
                'title_template': 'Loan Disbursed',
                'body_template': 'KSh {amount} has been disbursed to your account from {chama_name}. Repayments start {start_date}.',
                'sms_template': 'Sacco Bridge: KSh {amount} disbursed from {chama_name}. First repayment due {start_date}.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/chamas/{chama_id}/loans/{loan_id}',
            },
            {
                'name': 'chama_loan_repayment_reminder',
                'category': NotificationCategory.CHAMA_LOAN,
                'title_template': 'Loan Repayment Reminder',
                'body_template': 'Your loan repayment of KSh {amount} to {chama_name} is due {due_date}. Outstanding balance: KSh {balance}.',
                'sms_template': 'Sacco Bridge: Reminder - KSh {amount} loan repayment due {due_date}. Balance: KSh {balance}.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/chamas/{chama_id}/loans/{loan_id}',
            },
            # Connection notifications
            {
                'name': 'buyer_interest_received',
                'category': NotificationCategory.LIQUIDITY_REQUEST,
                'title_template': 'New Buyer Interest',
                'body_template': 'A buyer is interested in your {share_quantity} shares in {sacco_name}. Tap to review.',
                'sms_template': 'Sacco Bridge: A buyer is interested in your shares. Review in app.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/requests/{request_id}',
            },
            {
                'name': 'offer_received',
                'category': NotificationCategory.OFFER,
                'title_template': 'New Offer Received',
                'body_template': '{offeror_name} offered KSh {price_per_share}/share for your {share_quantity} shares in {sacco_name}. Total: KSh {total_amount}.',
                'sms_template': 'Sacco Bridge: New offer of KSh {total_amount} for your shares. Review in app.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/connections/{connection_id}',
            },
            {
                'name': 'offer_accepted',
                'category': NotificationCategory.OFFER,
                'title_template': 'Offer Accepted',
                'body_template': 'Your offer of KSh {total_amount} for {share_quantity} shares in {sacco_name} has been accepted. Settlement will begin shortly.',
                'sms_template': 'Sacco Bridge: Offer accepted. Settlement beginning for KSh {total_amount}.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/connections/{connection_id}',
            },
            # Account and security notifications
            {
                'name': 'account_verification',
                'category': NotificationCategory.ACCOUNT,
                'title_template': 'Verify Your Account',
                'body_template': 'Welcome to Sacco Bridge! Use code {otp} to verify your {verification_type}.',
                'sms_template': 'Sacco Bridge verification code: {otp}. Expires in 24 hours.',
                'default_channels': [NotificationChannel.SMS, NotificationChannel.EMAIL],
                'default_priority': NotificationPriority.HIGH,
            },
            {
                'name': 'security_login_alert',
                'category': NotificationCategory.SECURITY,
                'title_template': 'New Login Detected',
                'body_template': 'A new login was detected on your account from {device_type} in {location}. If this was not you, secure your account immediately.',
                'sms_template': 'Sacco Bridge: New login from {device_type}. Not you? Contact support.',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.URGENT,
            },
            {
                'name': 'chama_meeting_reminder',
                'category': NotificationCategory.CHAMA_MEETING,
                'title_template': 'Meeting Reminder',
                'body_template': '{chama_name} meeting: {meeting_title} on {meeting_date} at {meeting_time}. Location: {location}.',
                'sms_template': 'Sacco Bridge: {chama_name} meeting {meeting_date} at {meeting_time}. {location}',
                'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
                'default_priority': NotificationPriority.HIGH,
                'action_url_template': '/chamas/{chama_id}/meetings/{meeting_id}',
            },
        ]

        created_count = 0
        for template_data in templates:
            template, created = NotificationTemplate.objects.update_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created template: {template.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} new notification templates.'
            )
        )