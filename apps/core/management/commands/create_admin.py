import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates or updates default admin user from environment variables'

    def handle(self, *args, **options):
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')

        if not email or not password:
            self.stdout.write('ADMIN_EMAIL or ADMIN_PASSWORD not set. Skipping.')
            return

        from apps.users.models import Role

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': 'Platform',
                'last_name': 'Administrator',
                'phone_number': '0700000000',
                'email_verified': True,
                'phone_verified': True,
                'is_staff': True,
                'is_superuser': True,
            }
        )

        if created:
            user.set_password(password)
            user.save()
            user.add_role(Role.PLATFORM_ADMIN)
            user.add_role(Role.SUPPORT_AGENT)
            self.stdout.write(self.style.SUCCESS(f'Admin user {email} created with roles.'))
        else:
            updated = False
            if not user.email_verified:
                user.email_verified = True
                updated = True
            if not user.phone_verified:
                user.phone_verified = True
                updated = True
            if not user.is_staff:
                user.is_staff = True
                updated = True
            if not user.is_superuser:
                user.is_superuser = True
                updated = True
            if user.check_password(password) is False:
                user.set_password(password)
                updated = True
            
            # Ensure roles are assigned
            if not user.has_role(Role.PLATFORM_ADMIN):
                user.add_role(Role.PLATFORM_ADMIN)
                updated = True
            if not user.has_role(Role.SUPPORT_AGENT):
                user.add_role(Role.SUPPORT_AGENT)
                updated = True

            if updated:
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Admin user {email} updated with roles.'))
            else:
                self.stdout.write(f'Admin user {email} already up to date.')