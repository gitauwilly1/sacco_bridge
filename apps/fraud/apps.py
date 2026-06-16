from django.apps import AppConfig


class FraudConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.fraud'
    verbose_name = 'Fraud Detection'
    label = 'fraud'

    def ready(self):
        import apps.fraud.signals