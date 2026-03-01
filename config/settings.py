import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
DEBUG = os.environ.get('DJANGO_DEBUG') == '1'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = ['django.contrib.admin', # Admin panel
                  'django.contrib.auth', # User authentication
                  'django.contrib.contenttypes', # Content type system
                  'django.contrib.sessions', # Session framework
                  'django.contrib.messages', # Messaging framework
                  'django.contrib.staticfiles', # Static file handling
                  'rest_framework', # Django REST Framework for API development
                  'app'] # Our app

MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', # Security headers
              'whitenoise.middleware.WhiteNoiseMiddleware', # White noise: Serve static files by Django (not by web server)
              'django.contrib.sessions.middleware.SessionMiddleware', # Read/write session cookies
              'django.middleware.common.CommonMiddleware', # URL normalization and other common tasks
              'django.middleware.csrf.CsrfViewMiddleware', # CSRF protection: Prevent malicious websites from submitting forms on your behalf
              'django.contrib.auth.middleware.AuthenticationMiddleware', # Attach user.request to every request
              'django.contrib.messages.middleware.MessageMiddleware'] # Flash message support

ROOT_URLCONF = 'config.urls' # Starts URL matching from config/urls.py

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates', # # Use Django's built-in templates
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': { # Add variables to templates
                    'context_processors': ['django.template.context_processors.debug',
                                            'django.template.context_processors.request',
                                            'django.contrib.auth.context_processors.auth',
                                            'django.contrib.messages.context_processors.messages']
        }
    }
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database configuration
DATABASES = {
    'default': {'ENGINE': 'django.db.backends.postgresql', # Set PostgreSQL as the database engine
                'NAME': os.environ.get('POSTGRES_DB'),
                'USER': os.environ.get('POSTGRES_USER'),
                'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
                'HOST': os.environ.get('DB_HOST'),
                'PORT': os.environ.get('DB_PORT')
    }
}

# SSL encryption for Azure database connection
if os.environ.get('DB_SSLMODE'):
    DATABASES['default']['OPTIONS'] = {'sslmode': os.environ['DB_SSLMODE']} 

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT auth
                                       'rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated']
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=1),
}

SESSION_COOKIE_AGE = 60 * 60  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True  # reset expiry on each request

LOGIN_URL = '/login/'

CSRF_TRUSTED_ORIGINS = ['https://*.azurecontainerapps.io',
                        'http://localhost:8000',
                        'http://127.0.0.1:8000']

# OpenAI
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_CHAT_MODEL = os.environ.get('OPENAI_CHAT_MODEL')
OPENAI_ANALYSIS_MODEL = os.environ.get('OPENAI_ANALYSIS_MODEL')
OPENAI_EMBEDDING_MODEL = os.environ.get('OPENAI_EMBEDDING_MODEL')

# Interviews
NUM_INTERVIEWS = os.environ.get('NUM_INTERVIEWS')
