"""
Management command to create default roles and permissions.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.users.models import User, Role


class Command(BaseCommand):
    help = 'Creates default roles and assigns permissions for Sacco Bridge'

    def handle(self, *args, **options):
        self.stdout.write('Creating default roles...')

        roles_permissions = {
            Role.PLATFORM_ADMIN: {
                'description': 'Full platform access with administrative privileges',
                'permissions': [
                    'view_user', 'change_user', 'delete_user',
                    'view_chama', 'change_chama', 'delete_chama',
                    'view_contribution', 'change_contribution',
                    'view_loan', 'change_loan', 'approve_loan',
                    'view_settlement', 'manage_settlement',
                    'view_dispute', 'resolve_dispute',
                    'view_analytics', 'export_data',
                ]
            },
            Role.CHAMA_TREASURER: {
                'description': 'Manages chama finances, contributions, and loans',
                'permissions': [
                    'view_chama', 'manage_chama_finances',
                    'create_contribution', 'view_contribution',
                    'approve_loan', 'view_loan',
                    'manage_members', 'view_chama_reports',
                ]
            },
            Role.CHAMA_CHAIRPERSON: {
                'description': 'Oversees chama operations and member management',
                'permissions': [
                    'view_chama', 'manage_members',
                    'approve_loan', 'view_chama_reports',
                    'manage_chama_settings',
                ]
            },
            Role.CHAMA_SECRETARY: {
                'description': 'Manages chama records, meetings, and communications',
                'permissions': [
                    'view_chama', 'manage_meetings',
                    'view_contribution', 'view_loan',
                    'send_announcements', 'manage_chama_records',
                ]
            },
            Role.CHAMA_MEMBER: {
                'description': 'Regular chama member with basic access',
                'permissions': [
                    'view_chama', 'make_contribution',
                    'request_loan', 'view_own_records',
                ]
            },
            Role.INVESTOR: {
                'description': 'Buys SACCO shares from sellers seeking liquidity',
                'permissions': [
                    'view_sacco_listings', 'express_interest',
                    'make_offer', 'view_own_settlements',
                ]
            },
            Role.SELLER: {
                'description': 'Sells SACCO shares to access liquidity',
                'permissions': [
                    'create_liquidity_request', 'view_buyer_offers',
                    'accept_offer', 'view_own_settlements',
                ]
            },
            Role.INSTITUTIONAL_BUYER: {
                'description': 'Institutional entity buying SACCO shares',
                'permissions': [
                    'view_sacco_listings', 'express_interest',
                    'make_offer', 'bulk_purchase',
                    'view_settlements',
                ]
            },
            Role.SUPPORT_AGENT: {
                'description': 'Handles customer support and dispute resolution',
                'permissions': [
                    'view_user', 'view_chama',
                    'view_settlement', 'manage_dispute',
                    'view_support_tickets',
                ]
            },
        }

        for role, config in roles_permissions.items():
            self.stdout.write(f'  Setting up {role} role...')

            for perm_name in config['permissions']:
                Permission.objects.get_or_create(
                    codename=perm_name,
                    defaults={
                        'name': f'Can {perm_name.replace("_", " ")}',
                        'content_type': ContentType.objects.get_or_create(
                            app_label='sacco_bridge',
                            model='custompermission'
                        )[0]
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully created default roles and permissions.'))