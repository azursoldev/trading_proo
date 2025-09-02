"""
Production settings for Trading Pro project on Azure.
"""

import os
import dj_database_url
from decouple import config
from .settings import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-vjkw1a)_d6!ru96#3^&p8rcll6!tkwrgcqdo7w!qmz421(h1mn')

# Azure App Service hostnames
ALLOWED_HOSTS = [
    'trading-pro-app.azurewebsites.net',
    'trading-pro-app.scm.azurewebsites.net',
    '127.0.0.1',
    'localhost',
    '.azurewebsites.net',
]

# Database configuration for Azure PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'psql_admin',
        'PASSWORD': 'NqBHWBE9EhVltj16fjuq',
        'HOST': 'newstradingapplication.postgres.database.azure.com',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Static files configuration for Azure
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise configuration for serving static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS settings (Azure handles SSL termination)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
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
        'main_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Email configuration (using Azure SendGrid or similar)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.sendgrid.net')
EMAIL_PORT = config('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Cache configuration (using Azure Redis Cache)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
    }
}

# OpenAI API configuration
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# Interactive Brokers configuration
IB_HOST = config('IB_HOST', default='127.0.0.1')
IB_PORT = config('IB_PORT', default=7497)
IB_CLIENT_ID = config('IB_CLIENT_ID', default=1)

# Azure Storage configuration for file uploads
AZURE_STORAGE_ACCOUNT_NAME = config('AZURE_STORAGE_ACCOUNT_NAME', default='')
AZURE_STORAGE_ACCOUNT_KEY = config('AZURE_STORAGE_ACCOUNT_KEY', default='')
AZURE_STORAGE_CONTAINER = config('AZURE_STORAGE_CONTAINER', default='trading-pro-files')

# API Rate limiting
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
