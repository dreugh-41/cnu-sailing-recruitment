import os
import dj_database_url
from pathlib import Path

# Security settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-local-development')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,cnu-recruitment.onrender.com').split(',')
BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:////' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Static files settings
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Security additions
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost,http://127.0.0.1').split(',')