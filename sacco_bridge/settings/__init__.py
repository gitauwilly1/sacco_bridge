import os

ENVIRONMENT = os.environ.get('DJANGO_SETTINGS_MODULE', 'sacco_bridge.settings')

if 'production' in ENVIRONMENT:
    from .production import *
else:
    from .base import *