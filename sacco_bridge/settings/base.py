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
)

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production
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
    'rest_framework_simplejwt.token_blacklist',
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
    'channels',
    'django_celery_beat',
    'django_celery_results',
    'auditlog',
    'import_export',
    'django_extensions',
    'cloudinary',
    'cloudinary_storage',
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
    'apps.mpesa',
    'apps.receipts',
    'apps.legal',
    'apps.reports',
    'apps.activity',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middleware configuration
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

# Database configuration
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Redis configuration
REDIS_URL = env('REDIS_URL')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Channel layers for WebSockets
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [{
                'address': REDIS_URL,
            }],
        },
    },
}

# Celery configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Nairobi'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Custom user model
AUTH_USER_MODEL = 'users.User'

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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
}

# Use Cloudinary for media files if configured
CLOUDINARY_ENABLED = all([
    env('CLOUDINARY_CLOUD_NAME', default=''),
    env('CLOUDINARY_API_KEY', default=''),
    env('CLOUDINARY_API_SECRET', default=''),
])

if CLOUDINARY_ENABLED:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Site ID for django.contrib.sites
SITE_ID = 1

# Frontend URL for email links
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')

# Default from email
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@saccobridge.co.ke')

# CORS configuration
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True

# REST Framework configuration
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
        'apps.core.throttling.ReadRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'auth': '5/minute',
        'auth_anon': '3/minute',
        'mutation': '20/minute',
        'read': '100/minute',
        'sensitive': '3/minute',
        'bulk': '5/minute',
        'report': '5/hour',
    },
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=7),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Django AllAuth configuration
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
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
        }
    }
}

# Axes configuration (Brute force protection)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_LOCKOUT_CALLABLE = 'apps.users.callbacks.user_locked_out'
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = ['username']
AXES_LOCKOUT_URL = '/api/v1/auth/locked-out/'

# Spectacular settings for OpenAPI/Swagger
SPECTACULAR_SETTINGS = {
    'TITLE': 'Sacco Bridge API',
    'DESCRIPTION': """
    API for Sacco Bridge - a dual-mode platform digitizing chama management 
    and facilitating secondary market liquidity for SACCO shares.
    
    Features include:
    - User registration and authentication (JWT, Google OAuth, 2FA TOTP)
    - Role-based access control (10 distinct roles)
    - Chama digitization with automated M-Pesa contribution tracking
    - Digital loan management (apply, approve, disburse, repay)
    - Meeting scheduling with attendance tracking
    - Bulk contribution recording for treasurers
    - SACCO share liquidity connections between verified buyers and sellers
    - Structured offer negotiation (make, accept, decline, counter)
    - Atomic settlement coordination with 11-state machine
    - Trustee-backed settlement guarantees
    - Structured dispute resolution with immutable audit trails
    - Real-time WebSocket notifications and AI chatbot
    - Firebase push notifications, Africa's Talking SMS, and email delivery
    - PDF receipt generation with QR verification codes
    - M-Pesa STK push integration for mobile payments
    - Analytics dashboards with precomputed metrics
    - Comprehensive API documentation with drf-spectacular
    """,
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,

    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
        'filter': True,
    },

    'SECURITY': [
        {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
                'description': 'Enter your JWT access token'
            }
        }
    ],

    'TAGS': [
        {'name': 'Authentication', 'description': 'User registration, login, token refresh, 2FA setup, password management, and Google OAuth.'},
        {'name': 'Users', 'description': 'User profile management, detailed profiles with KYC, and login history.'},
        {'name': 'Chamas', 'description': 'Chama creation, retrieval, updates, join/leave, and member management.'},
        {'name': 'Contributions', 'description': 'Single and bulk contribution recording, listing, and verification for chama groups.'},
        {'name': 'Loans', 'description': 'Loan application, approval, disbursement, repayment tracking within chamas.'},
        {'name': 'Meetings', 'description': 'Meeting scheduling, listing, and attendance recording for chama groups.'},
        {'name': 'Investments', 'description': 'SACCO browsing, share holdings, liquidity requests, buyer opportunities, and connections.'},
        {'name': 'Settlements', 'description': 'Settlement tracking with full audit trail, event timeline, ledger entries, and dispute resolution.'},
        {'name': 'Notifications', 'description': 'In-app notification list, unread counts, mark read, device registration, and channel preferences.'},
        {'name': 'Analytics', 'description': 'User and platform dashboards, chama analytics, SACCO market data, and metrics refresh.'},
        {'name': 'Chatbot', 'description': 'AI-powered chat sessions with Google Gemini, knowledge base articles, and conversation context.'},
        {'name': 'M-Pesa', 'description': 'STK push initiation, transaction listing, and payment status tracking via Safaricom Daraja API.'},
        {'name': 'Receipts', 'description': 'PDF receipt listing, detail retrieval, and download for settlements, contributions, and repayments.'},
    ],
}

# Encryption key for sensitive data
ENCRYPTION_KEY = env('ENCRYPTION_KEY')

# Logging configuration
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
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Session and security settings
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Email backend - override with console for development
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# M-Pesa Daraja API Configuration
MPESA_CONSUMER_KEY = env('MPESA_CONSUMER_KEY')
MPESA_CONSUMER_SECRET = env('MPESA_CONSUMER_SECRET')
MPESA_PASSKEY = env('MPESA_PASSKEY')
MPESA_SHORTCODE = env('MPESA_SHORTCODE')
MPESA_CALLBACK_URL = env('MPESA_CALLBACK_URL')

# Gemini AI Configuration
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GEMINI_MODEL = env('GEMINI_MODEL', default='gemini-2.5-flash')

# CELERY BEAT SCHEDULE

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Settlement recovery - runs every 5 minutes
    'recover-stuck-settlements': {
        'task': 'apps.transactions.tasks.recover_stuck_settlements',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'settlements'},
    },

    # Analytics aggregation - runs daily at 2:00 AM
    'aggregate-platform-metrics': {
        'task': 'apps.analytics.tasks.aggregate_daily_platform_metrics',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'analytics'},
    },

    # SACCO disclosure check - runs daily at 8:00 AM
    'check-sacco-disclosures': {
        'task': 'apps.investments.tasks.check_stale_disclosures',
        'schedule': crontab(hour=8, minute=0),
        'options': {'queue': 'maintenance'},
    },

    # Contribution deadline reminders - runs daily at 7:00 AM
    'contribution-deadline-reminders': {
        'task': 'apps.chamas.tasks.send_contribution_reminders',
        'schedule': crontab(hour=7, minute=0),
        'options': {'queue': 'notifications'},
    },

    # Loan repayment reminders - runs daily at 8:00 AM
    'loan-repayment-reminders': {
        'task': 'apps.chamas.tasks.send_loan_repayment_reminders',
        'schedule': crontab(hour=8, minute=0),
        'options': {'queue': 'notifications'},
    },

    # M-Pesa reconciliation - runs every 30 minutes
    'reconcile-mpesa-transactions': {
        'task': 'apps.mpesa.tasks.reconcile_pending_mpesa_transactions',
        'schedule': crontab(minute='*/30'),
        'options': {'queue': 'payments'},
    },

    # Notification retry - runs every 10 minutes
    'retry-failed-notifications': {
        'task': 'apps.notifications.tasks.retry_failed_deliveries',
        'schedule': crontab(minute='*/10'),
        'options': {'queue': 'notifications'},
    },

    # Cleanup old data - runs weekly on Sunday at 3:00 AM
    'cleanup-expired-data': {
        'task': 'apps.core.tasks.cleanup_expired_data',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
        'options': {'queue': 'maintenance'},
    },

    # Chama analytics aggregation - runs weekly on Monday at 4:00 AM
    'aggregate-chama-analytics': {
        'task': 'apps.analytics.tasks.aggregate_weekly_chama_analytics',
        'schedule': crontab(hour=4, minute=0, day_of_week=1),
        'options': {'queue': 'analytics'},
    },
}

# Test configuration
if 'test' in os.environ.get('DJANGO_SETTINGS_MODULE', ''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    
    # Use local memory cache instead of Redis for tests
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    
    # Disable throttling in tests
    REST_FRAMEWORK = {
        **REST_FRAMEWORK,
        'DEFAULT_THROTTLE_CLASSES': [],
    }
    
    # reCAPTCHA
RECAPTCHA_SITE_KEY = env('RECAPTCHA_SITE_KEY', default='')
RECAPTCHA_SECRET_KEY = env('RECAPTCHA_SECRET_KEY', default='')