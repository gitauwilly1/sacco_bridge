import os
from pathlib import Path
from datetime import timedelta
import environ

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# CORE DJANGO SETTINGS

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'axes',
    'guardian',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'channels',
    'django_celery_beat',
    'django_celery_results',
    'auditlog',
    'import_export',
    'django_extensions',
    'health_check',
    'health_check.db',
    'health_check.cache',
    'health_check.contrib.celery',
    'health_check.contrib.redis',
]

LOCAL_APPS = [
    'apps.core',
    'apps.users',
    'apps.chamas',
    'apps.investments',
    'apps.transactions',
    'apps.notifications',
    'apps.analytics',
    'apps.chatbot',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIDDLEWARE

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'apps.core.middleware.RequestLoggingMiddleware',
    'apps.core.middleware.APIVersionMiddleware',
    'apps.core.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'sacco_bridge.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sacco_bridge.wsgi.application'
ASGI_APPLICATION = 'sacco_bridge.asgi.application'

# DATABASE

DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Connection pooling for PostgreSQL
CONN_MAX_AGE = 60
CONN_HEALTH_CHECKS = True

# REDIS & CACHING

REDIS_URL = env('REDIS_URL')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'sacco_bridge',
        'TIMEOUT': 300,
    }
}

# Session cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'

# CHANNELS (WebSockets)

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [{
                'address': REDIS_URL,
            }],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# CELERY

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Nairobi'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_RESULT_EXPIRES = timedelta(days=7)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    'aggregate-platform-metrics': {
        'task': 'apps.analytics.tasks.aggregate_platform_metrics',
        'schedule': timedelta(hours=1),
        'options': {'queue': 'analytics'},
    },
    'aggregate-sacco-market-data': {
        'task': 'apps.analytics.tasks.aggregate_sacco_market_data',
        'schedule': timedelta(hours=6),
        'options': {'queue': 'analytics'},
    },
    'recover-stuck-settlements': {
        'task': 'apps.transactions.tasks.recover_stuck_settlements',
        'schedule': timedelta(minutes=5),
        'options': {'queue': 'settlements'},
    },
    'check-sacco-disclosures': {
        'task': 'apps.investments.tasks.check_sacco_disclosures',
        'schedule': timedelta(hours=24),
        'options': {'queue': 'maintenance'},
    },
    'cleanup-expired-tokens': {
        'task': 'apps.users.tasks.cleanup_expired_tokens',
        'schedule': timedelta(hours=24),
        'options': {'queue': 'maintenance'},
    },
    'send-pending-notifications': {
        'task': 'apps.notifications.tasks.send_pending_notifications',
        'schedule': timedelta(minutes=1),
        'options': {'queue': 'notifications'},
    },
    'generate-scheduled-reports': {
        'task': 'apps.analytics.tasks.generate_scheduled_reports',
        'schedule': timedelta(hours=1),
        'options': {'queue': 'analytics'},
    },
}

# AUTHENTICATION

AUTH_USER_MODEL = 'users.User'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'apps.core.validators.SpecialCharacterValidator',
    },
    {
        'NAME': 'apps.core.validators.UppercaseLowercaseValidator',
    },
]

LOGIN_URL = '/api/v1/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# DJANGO ALLAUTH

ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_SESSION_REMEMBER = True

SOCIALACCOUNT_ADAPTER = 'allauth.socialaccount.adapter.DefaultSocialAccountAdapter'
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': env('GOOGLE_CLIENT_ID'),
            'secret': env('GOOGLE_CLIENT_SECRET'),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'VERIFIED_EMAIL': True,
    }
}

# JWT (Simple JWT)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'sacco_bridge',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=30),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}

# AXES (Brute Force Protection)

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = 'apps.users.callbacks.user_locked_out'
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
AXES_USERNAME_FORM_FIELD = 'email'
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
AXES_ONLY_USER_FAILURES = False
AXES_LOCKOUT_URL = '/api/v1/auth/locked-out/'
AXES_VERBOSE = True
AXES_HANDLER = 'axes.handlers.database.AxesDatabaseHandler'

# DJANGO GUARDIAN (Object-level permissions)

GUARDIAN_RAISE_403 = True
ANONYMOUS_USER_NAME = None

# CORS

CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-version',
]
CORS_EXPOSE_HEADERS = [
    'x-request-id',
    'x-response-time',
    'x-api-version',
]
CORS_PREFLIGHT_MAX_AGE = 86400

# REST FRAMEWORK

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.CustomPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth': '20/minute',
        'settlement': '50/minute',
        'chatbot': '30/minute',
    },
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'NUM_PROXIES': 1,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'TEST_REQUEST_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# SPECTACULAR (OpenAPI / Swagger)

SPECTACULAR_SETTINGS = {
    'TITLE': 'Sacco Bridge API',
    'DESCRIPTION': '''
    Sacco Bridge is a dual-mode platform that digitizes chama (informal savings group) 
    management and facilitates secondary market liquidity for SACCO shares.
    
    ## Key Features
    - Chama digitization with automated M-Pesa contribution tracking
    - Digital loan management within chamas
    - SACCO share liquidity connections between verified buyers and sellers
    - Atomic settlement coordination with trustee-backed guarantees
    - Structured dispute resolution with immutable audit trails
    - AI-powered support chatbot (Google Gemini)
    - Real-time notifications via Firebase Cloud Messaging
    
    ## Authentication
    All API endpoints (except registration and login) require JWT authentication.
    Include the token in the Authorization header: `Bearer <your-token>`
    
    ## Rate Limiting
    - Anonymous: 100 requests/hour
    - Authenticated: 1000 requests/hour
    - Auth endpoints: 20/minute
    - Settlement endpoints: 50/minute
    - Chatbot: 30/minute
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'SECURITY': [
        {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    ],
    'TAGS': [
        {'name': 'Authentication', 'description': 'User registration, login, and token management'},
        {'name': 'Users', 'description': 'User profile management and settings'},
        {'name': 'Chamas', 'description': 'Chama creation, management, and member operations'},
        {'name': 'Contributions', 'description': 'Chama contribution tracking and M-Pesa integration'},
        {'name': 'Loans', 'description': 'Chama loan requests, approvals, and repayments'},
        {'name': 'Investments', 'description': 'SACCO share liquidity requests and connections'},
        {'name': 'Settlements', 'description': 'Transaction settlement tracking and dispute resolution'},
        {'name': 'Notifications', 'description': 'Push notifications, SMS, and email alerts'},
        {'name': 'Analytics', 'description': 'Platform analytics and reporting'},
        {'name': 'Chatbot', 'description': 'AI-powered support assistant'},
    ],
    'SORT_OPERATIONS': False,
    'ENUM_NAME_OVERRIDES': {},
}

# INTERNATIONALIZATION

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True
USE_L10N = True

LANGUAGES = [
    ('en', 'English'),
    ('sw', 'Kiswahili'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# STATIC & MEDIA FILES

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880   # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Maximum image upload size
MAX_IMAGE_UPLOAD_SIZE = 5242880  # 5MB

# DEFAULT MODEL FIELD

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# SITE & URLS

SITE_ID = 1
SITE_NAME = 'Sacco Bridge'
SITE_DOMAIN = env('SITE_DOMAIN', default='localhost:8000')

FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')
BACKEND_URL = env('BACKEND_URL', default='http://localhost:8000')

# EMAIL

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@saccobridge.co.ke')
SERVER_EMAIL = env('SERVER_EMAIL', default='server@saccobridge.co.ke')
EMAIL_SUBJECT_PREFIX = '[Sacco Bridge] '
ADMINS = [('Sacco Bridge Admin', env('ADMIN_EMAIL', default='admin@saccobridge.co.ke'))]
MANAGERS = ADMINS

# SMS (Africa's Talking)

AFRICASTALKING_USERNAME = env('AFRICASTALKING_USERNAME', default='sandbox')
AFRICASTALKING_API_KEY = env('AFRICASTALKING_API_KEY', default='')
AFRICASTALKING_SENDER_ID = env('AFRICASTALKING_SENDER_ID', default='SaccoBridge')

# M-PESA (Safaricom Daraja)

MPESA_CONSUMER_KEY = env('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = env('MPESA_CONSUMER_SECRET', default='')
MPESA_PASSKEY = env('MPESA_PASSKEY', default='')
MPESA_SHORTCODE = env('MPESA_SHORTCODE', default='174379')
MPESA_CALLBACK_URL = env('MPESA_CALLBACK_URL', default='')
MPESA_ENVIRONMENT = env('MPESA_ENVIRONMENT', default='sandbox')

# GOOGLE GEMINI AI

GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GEMINI_MODEL = env('GEMINI_MODEL', default='gemini-1.5-flash')

# FIREBASE CLOUD MESSAGING

FIREBASE_CREDENTIALS_PATH = env('FIREBASE_CREDENTIALS_PATH', default='')

# ENCRYPTION

ENCRYPTION_KEY = env('ENCRYPTION_KEY')

# SENTRY (Error Tracking)

SENTRY_DSN = env('SENTRY_DSN', default='')

if SENTRY_DSN and not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        send_default_pii=False,
        environment=env('ENVIRONMENT', default='development'),
        release=env('RELEASE_VERSION', default='1.0.0'),
    )

# LOGGING

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
            'style': '%',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'sacco_bridge.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'sacco_bridge_error.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['mail_admins', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['mail_admins', 'error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'axes': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# SECURITY

# HTTPS settings
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Session security
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# CSRF
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = env('CSRF_TRUSTED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])

# Browser security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# AUDIT LOG

AUDITLOG_INCLUDE_TRACKING_MODELS = (
    'users.User',
    'users.UserRole',
    'chamas.Chama',
    'chamas.Contribution',
    'chamas.Loan',
    'investments.SACCO',
    'investments.LiquidityRequest',
    'investments.Connection',
    'investments.Offer',
    'transactions.SettlementIntent',
)

AUDITLOG_INCLUDE_TRACKING_FIELDS = '__all__'
AUDITLOG_EXCLUDE_TRACKING_FIELDS = (
    'password',
    'totp_secret',
    'email_verification_code',
    'phone_verification_code',
)

# HEALTH CHECK

HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,
    'MEMORY_MIN': 100,
}

# MISC

# Silence misleading system checks
SILENCED_SYSTEM_CHECKS = [
    'django_recaptcha.recaptcha_test_key_error',
    'axes.W003',
]