import os

# Set environment variables BEFORE importing main settings
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-secret-key-for-testing-only')
os.environ.setdefault('DJANGO_DEBUG', '1')
os.environ.setdefault('NUM_CONCURRENT_INTERVIEWS', '2')
os.environ.setdefault('OPENAI_API_KEY', 'test-openai-key')
os.environ.setdefault('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
os.environ.setdefault('OPENAI_ANALYSIS_MODEL', 'gpt-4o-mini')
os.environ.setdefault('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
os.environ.setdefault('NUM_INTERVIEWS', '5')
os.environ.setdefault('POSTGRES_DB', 'test_db')
os.environ.setdefault('POSTGRES_USER', 'test_user')
os.environ.setdefault('POSTGRES_PASSWORD', 'test_pass')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')

from config.settings import *  # noqa: F401, F403

# Use SQLite in-memory for fast tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable whitenoise compressed storage in tests
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    }
}

# Speed up password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
