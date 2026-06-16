from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet


def get_fernet():
    key = settings.ENCRYPTION_KEY.encode()
    return Fernet(key)


class EncryptedTextField(models.TextField):

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        try:
            return get_fernet().encrypt(str(value).encode()).decode()
        except Exception:
            return value

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value

    def to_python(self, value):
        if value is None or value == '':
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value


class EncryptedCharField(models.CharField):

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        try:
            return get_fernet().encrypt(str(value).encode()).decode()
        except Exception:
            return value

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value

    def to_python(self, value):
        if value is None or value == '':
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value