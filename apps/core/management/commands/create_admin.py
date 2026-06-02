import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates default admin user from environment variables'

    def handle(self, *args, **options):
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')

        if not email or not password:
            self.stdout.write('ADMIN_EMAIL or ADMIN_PASSWORD not set. Skipping.')
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(f'Admin user {email} already exists.')
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Platform',
            last_name='Administrator',
            phone_number='0700000000',
        )

        self.stdout.write(self.style.SUCCESS(f'Admin user {email} created.'))