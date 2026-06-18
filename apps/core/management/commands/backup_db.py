import os
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create a database backup'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, help='Output file path')
        parser.add_argument('--compress', action='store_true', default=True)

    def handle(self, *args, **options):
        db_settings = settings.DATABASES['default']
        engine = db_settings['ENGINE']

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        if 'postgresql' in engine:
            self._backup_postgres(db_settings, backup_dir, timestamp, options)
        elif 'sqlite' in engine:
            self._backup_sqlite(db_settings, backup_dir, timestamp, options)
        else:
            self.stderr.write(self.style.ERROR(f'Unsupported engine: {engine}'))
            return

        # Cleanup old backups (keep last 30 days)
        self._cleanup_old_backups(backup_dir, days=30)

    def _backup_postgres(self, db_settings, backup_dir, timestamp, options):
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_host = db_settings.get('HOST', 'localhost')
        db_port = db_settings.get('PORT', '5432')

        filename = f'backup_{db_name}_{timestamp}.sql'
        filepath = os.path.join(backup_dir, filename)

        cmd = [
            'pg_dump',
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '-f', filepath,
            '--no-owner',
            '--no-acl',
        ]

        env = os.environ.copy()
        env['PGPASSWORD'] = db_settings.get('PASSWORD', '')

        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)

            if options.get('compress'):
                import gzip
                gz_filepath = filepath + '.gz'
                with open(filepath, 'rb') as f_in:
                    with gzip.open(gz_filepath, 'wb') as f_out:
                        f_out.writelines(f_in)
                os.remove(filepath)
                filepath = gz_filepath

            file_size = os.path.getsize(filepath)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Backup created: {filepath} ({file_size / 1024 / 1024:.1f}MB)'
                )
            )

        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f'Backup failed: {e.stderr}'))

    def _backup_sqlite(self, db_settings, backup_dir, timestamp, options):
        import shutil
        db_path = db_settings['NAME']
        filename = f'backup_sqlite_{timestamp}.db'
        filepath = os.path.join(backup_dir, filename)

        shutil.copy2(db_path, filepath)
        file_size = os.path.getsize(filepath)
        self.stdout.write(
            self.style.SUCCESS(f'Backup created: {filepath} ({file_size / 1024 / 1024:.1f}MB)')
        )

    def _cleanup_old_backups(self, backup_dir, days=30):
        import time
        cutoff = time.time() - (days * 86400)

        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                self.stdout.write(f'Removed old backup: {filename}')