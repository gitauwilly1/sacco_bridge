from django.apps import AppConfig


class EscrowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.escrow'
    verbose_name = 'Escrow'
    label = 'escrow'

    def ready(self):
        pass