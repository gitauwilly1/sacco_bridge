from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.users.models import Role


class Command(BaseCommand):
    help = 'Creates default roles and assigns permissions for Sacco Bridge'

    def handle(self, *args, **options):
        self.stdout.write('Creating default roles...')

        roles_permissions = {
            Role.PLATFORM_ADMIN: {
                'permissions': [
                    'view_user', 'change_user', 'delete_user',
                    'view_chama', 'change_chama', 'delete_chama',
                    'view_contribution', 'change_contribution',
                    'view_loan', 'change_loan',
                    'view_settlement', 'manage_settlement',
                    'view_dispute', 'resolve_dispute',
                    'view_analytics', 'export_data',
                ]
            },
            Role.SACCO_ADMIN: {
                'permissions': [
                    'view_sacco', 'change_sacco',
                    'view_sacco_listings', 'manage_sacco_members',
                ]
            },
            Role.INVESTOR: {
                'permissions': [
                    'view_sacco_listings', 'express_interest',
                    'make_offer', 'view_own_settlements',
                ]
            },
            Role.SELLER: {
                'permissions': [
                    'create_liquidity_request', 'view_buyer_offers',
                    'accept_offer', 'view_own_settlements',
                ]
            },
            Role.INSTITUTIONAL_BUYER: {
                'permissions': [
                    'view_sacco_listings', 'express_interest',
                    'make_offer', 'bulk_purchase',
                    'view_settlements',
                ]
            },
            Role.SUPPORT_AGENT: {
                'permissions': [
                    'view_user', 'view_chama',
                    'view_settlement', 'manage_dispute',
                    'view_support_tickets',
                ]
            },
        }

        content_type, _ = ContentType.objects.get_or_create(
            app_label='sacco_bridge',
            model='custompermission'
        )

        for role, config in roles_permissions.items():
            self.stdout.write(f'  Setting up {role} role...')
            for perm_name in config['permissions']:
                Permission.objects.get_or_create(
                    codename=perm_name,
                    defaults={
                        'name': f'Can {perm_name.replace("_", " ")}',
                        'content_type': content_type
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully created default roles and permissions.'))