from django.core.management.base import BaseCommand
from apps.notifications.models import (
    NotificationTemplate, NotificationCategory,
    NotificationPriority, NotificationChannel
)


class Command(BaseCommand):
    help = 'Creates default notification templates for Sacco Bridge with Swahili support'

    TEMPLATES = [
        # CHAMA CONTRIBUTION TEMPLATES
        {
            'name': 'chama_contribution_received',
            'category': NotificationCategory.CHAMA_CONTRIBUTION,
            'title_template': 'Contribution Received',
            'body_template': 'Your contribution of KSh {amount} to {chama_name} has been received.',
            'sms_template': 'KSh {amount} contribution to {chama_name} confirmed.',
            'email_subject_template': 'Contribution Confirmed - {chama_name}',
            'email_body_template': '<p>Your contribution of <strong>KSh {amount}</strong> to <strong>{chama_name}</strong> has been received.</p>',
            'sw_title_template': 'Mchango Umepokelewa',
            'sw_body_template': 'Mchango wako wa KSh {amount} kwa {chama_name} umepokelewa.',
            'sw_sms_template': 'KSh {amount} mchango kwa {chama_name} umethibitishwa.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.MEDIUM,
        },
        {
            'name': 'chama_contribution_reminder',
            'category': NotificationCategory.CHAMA_CONTRIBUTION,
            'title_template': 'Contribution Reminder',
            'body_template': 'Your contribution of KSh {amount} to {chama_name} is due by {due_date}.',
            'sms_template': 'Reminder: KSh {amount} contribution to {chama_name} due by {due_date}.',
            'sw_title_template': 'Kikumbusho cha Mchango',
            'sw_body_template': 'Mchango wako wa KSh {amount} kwa {chama_name} unatakiwa kufikia {due_date}.',
            'sw_sms_template': 'Kikumbusho: KSh {amount} mchango {chama_name} ifikapo {due_date}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.HIGH,
        },
        {
            'name': 'chama_contribution_overdue',
            'category': NotificationCategory.CHAMA_CONTRIBUTION,
            'title_template': 'Contribution Overdue',
            'body_template': 'Your contribution to {chama_name} is overdue. Late fee of KSh {late_fee} may apply.',
            'sms_template': 'Your {chama_name} contribution is overdue. Late fee may apply.',
            'sw_title_template': 'Mchango Umechelewa',
            'sw_body_template': 'Mchango wako kwa {chama_name} umechelewa. Ada ya kuchelewa ya KSh {late_fee} inaweza kutozwa.',
            'sw_sms_template': 'Mchango wako {chama_name} umechelewa. Ada inaweza kutozwa.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },

        # CHAMA LOAN TEMPLATES
        {
            'name': 'loan_request_submitted',
            'category': NotificationCategory.CHAMA_LOAN,
            'title_template': 'Loan Request Submitted',
            'body_template': 'Your loan request for KSh {amount} from {chama_name} has been submitted for review.',
            'sms_template': 'Loan request for KSh {amount} submitted to {chama_name}.',
            'sw_title_template': 'Ombi la Mkopo Limesilishwa',
            'sw_body_template': 'Ombi lako la mkopo wa KSh {amount} kutoka {chama_name} limesilishwa kwa mapitio.',
            'sw_sms_template': 'Ombi la mkopo KSh {amount} kwa {chama_name} limesilishwa.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.MEDIUM,
        },
        {
            'name': 'loan_approved',
            'category': NotificationCategory.CHAMA_LOAN,
            'title_template': 'Loan Approved',
            'body_template': 'Your loan of KSh {amount} from {chama_name} has been approved.',
            'sms_template': 'Loan of KSh {amount} approved by {chama_name}.',
            'sw_title_template': 'Mkopo Umeidhinishwa',
            'sw_body_template': 'Mkopo wako wa KSh {amount} kutoka {chama_name} umeidhinishwa.',
            'sw_sms_template': 'Mkopo wa KSh {amount} umeidhinishwa na {chama_name}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.HIGH,
        },
        {
            'name': 'loan_repayment_due',
            'category': NotificationCategory.CHAMA_LOAN,
            'title_template': 'Loan Repayment Due',
            'body_template': 'Your loan repayment of KSh {amount} to {chama_name} is due on {due_date}.',
            'sms_template': 'Loan repayment KSh {amount} due {due_date}.',
            'sw_title_template': 'Malipo ya Mkopo Yanadaiwa',
            'sw_body_template': 'Malipo yako ya mkopo wa KSh {amount} kwa {chama_name} yanadaiwa ifikapo {due_date}.',
            'sw_sms_template': 'Malipo ya mkopo KSh {amount} yanadaiwa {due_date}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.HIGH,
        },

        # INVESTMENT TEMPLATES
        {
            'name': 'buyer_interest_received',
            'category': NotificationCategory.INVESTMENT_CONNECTION,
            'title_template': 'Buyer Interested in Your Shares',
            'body_template': '{buyer_name} is interested in purchasing your {share_quantity} shares in {sacco_name}.',
            'sms_template': '{buyer_name} wants to buy your {sacco_name} shares.',
            'sw_title_template': 'Mnunuzi Amependezwa na Hisa Zako',
            'sw_body_template': '{buyer_name} ameonyesha nia ya kununua hisa zako {share_quantity} katika {sacco_name}.',
            'sw_sms_template': '{buyer_name} anataka kununua hisa zako za {sacco_name}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.HIGH,
        },
        {
            'name': 'offer_received',
            'category': NotificationCategory.INVESTMENT_OFFER,
            'title_template': 'New Offer Received',
            'body_template': '{offeror_name} offered KSh {price_per_share}/share for {quantity} shares in {sacco_name}.',
            'sw_title_template': 'Ofa Mpya Imepokelewa',
            'sw_body_template': '{offeror_name} ametoa KSh {price_per_share}/hisa kwa hisa {quantity} katika {sacco_name}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.HIGH,
        },
        {
            'name': 'offer_accepted',
            'category': NotificationCategory.INVESTMENT_OFFER,
            'title_template': 'Offer Accepted',
            'body_template': 'Your offer for {quantity} shares in {sacco_name} has been accepted. Settlement will begin shortly.',
            'sms_template': 'Your offer accepted. Settlement starting.',
            'sw_title_template': 'Ofa Imekubaliwa',
            'sw_body_template': 'Ofa yako ya hisa {quantity} katika {sacco_name} imekubaliwa. Malipo yataanza hivi karibuni.',
            'sw_sms_template': 'Ofa yako imekubaliwa. Malipo yanaanza.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },

        # SETTLEMENT TEMPLATES
        {
            'name': 'settlement_initiated',
            'category': NotificationCategory.SETTLEMENT,
            'title_template': 'Settlement Initiated',
            'body_template': 'Settlement for {quantity} shares in {sacco_name} (KSh {amount}) has been initiated.',
            'sw_title_template': 'Malipo Yameanzishwa',
            'sw_body_template': 'Malipo ya hisa {quantity} katika {sacco_name} (KSh {amount}) yameanzishwa.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.MEDIUM,
        },
        {
            'name': 'settlement_completed',
            'category': NotificationCategory.SETTLEMENT,
            'title_template': 'Settlement Complete',
            'body_template': 'Transaction complete: {quantity} shares in {sacco_name} transferred. Amount: KSh {amount}.',
            'sms_template': 'Transaction complete: {quantity} {sacco_name} shares. KSh {amount}.',
            'sw_title_template': 'Malipo Yamekamilika',
            'sw_body_template': 'Muamala umekamilika: hisa {quantity} katika {sacco_name} zimehamishwa. Kiasi: KSh {amount}.',
            'sw_sms_template': 'Muamala umekamilika: hisa {quantity} {sacco_name}. KSh {amount}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },
        {
            'name': 'settlement_disputed',
            'category': NotificationCategory.DISPUTE,
            'title_template': 'Transaction Under Review',
            'body_template': 'Your transaction #{reference} requires additional review. Our team is investigating.',
            'sms_template': 'Transaction #{reference} under review. We will update you.',
            'sw_title_template': 'Muamala Unachunguzwa',
            'sw_body_template': 'Muamala wako #{reference} unahitaji uchunguzi zaidi. Timu yetu inafanya uchunguzi.',
            'sw_sms_template': 'Muamala #{reference} unachunguzwa. Tutakujulisha.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },
        {
            'name': 'settlement_reversed',
            'category': NotificationCategory.SETTLEMENT,
            'title_template': 'Transaction Reversed',
            'body_template': 'Transaction #{reference} has been reversed. KSh {amount} returned.',
            'sms_template': 'Transaction #{reference} reversed. KSh {amount} returned.',
            'sw_title_template': 'Muamala Umerejeshwa',
            'sw_body_template': 'Muamala #{reference} umerejeshwa. KSh {amount} imerudishwa.',
            'sw_sms_template': 'Muamala #{reference} umerejeshwa. KSh {amount} imerudishwa.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },
        {
            'name': 'settlement_status_update',
            'category': NotificationCategory.SETTLEMENT_STATUS,
            'title_template': 'Settlement Status Update',
            'body_template': 'Your settlement #{reference} is now: {status}.',
            'sms_template': 'Settlement #{reference}: {status}.',
            'sw_title_template': 'Sasisho la Malipo',
            'sw_body_template': 'Malipo yako #{reference} sasa ni: {status}.',
            'sw_sms_template': 'Malipo #{reference}: {status}.',
            'default_channels': [NotificationChannel.IN_APP, NotificationChannel.PUSH],
            'default_priority': NotificationPriority.MEDIUM,
        },

        # SECURITY TEMPLATES
        {
            'name': 'login_alert',
            'category': NotificationCategory.SECURITY,
            'title_template': 'New Login Detected',
            'body_template': 'A new login was detected from {device} at {location}. If this was not you, secure your account.',
            'sms_template': 'New login from {device}. Not you? Secure your account.',
            'sw_title_template': 'Kuingia Kipya Kumegunduliwa',
            'sw_body_template': 'Kuingia kipya kumegunduliwa kutoka {device} katika {location}. Kama sio wewe, linda akaunti yako.',
            'sw_sms_template': 'Kuingia kipya kutoka {device}. Sio wewe? Linda akaunti.',
            'default_channels': [NotificationChannel.PUSH, NotificationChannel.SMS],
            'default_priority': NotificationPriority.URGENT,
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write('Creating notification templates with Swahili translations...')

        created_count = 0
        updated_count = 0

        for template_data in self.TEMPLATES:
            template, created = NotificationTemplate.objects.update_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created: {template.name}')
            else:
                updated_count += 1
                self.stdout.write(f'  Updated: {template.name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} new and updated {updated_count} '
                f'notification templates with Swahili translations.'
            )
        )