import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set DJANGO_SECRET_KEY to a random secret before starting.')
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
CSRF_TRUSTED_ORIGINS = [x for x in os.getenv('DJANGO_CSRF_ORIGINS', '').split(',') if x]
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','practice.apps.PracticeConfig']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','practice.middleware.AccessMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware','practice.middleware.HeadersMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','practice.content.website_content']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATA_DIR = Path(os.getenv('REREVI_DATA_DIR', str(BASE_DIR/'var')))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':DATA_DIR/'db.sqlite3','OPTIONS':{'timeout':20,'transaction_mode':'IMMEDIATE'}}}
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR/'staticfiles'
STATICFILES_DIRS = [BASE_DIR/'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
RESOURCE_ROOT = Path(os.getenv('REREVI_RESOURCE_ROOT', str(BASE_DIR/'resources'))).resolve()
PUBLIC_ACCESS = os.getenv('REREVI_PUBLIC_ACCESS', 'false').lower() == 'true'
PRIVATE_ACCESS_HASH = os.getenv('REREVI_PRIVATE_ACCESS_HASH', '')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO','https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60*60*12
SECURE_HSTS_SECONDS = 2592000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 2*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2*1024*1024
CACHES = {'default': {'BACKEND':'django.core.cache.backends.filebased.FileBasedCache','LOCATION':str(DATA_DIR/'cache'),'TIMEOUT':300,'OPTIONS':{'MAX_ENTRIES':2000}}}
LOGGING = {'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},'root':{'handlers':['console'],'level':'INFO'}}
STORAGES = {
    'default': {'BACKEND':'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND':'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'},
}
# Expiring answer snapshots are intentionally outside the backed-up database directory.
SHARE_DIR = Path(os.getenv('REREVI_SHARE_DIR', str(DATA_DIR.parent/'rerevi-shares'))).resolve()
PUBLIC_BASE_URL = os.getenv('REREVI_PUBLIC_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
LOGGING['filters'] = {'omit_share_urls': {'()':'practice.logging.OmitShareURLs'}}
LOGGING['handlers']['console']['filters'] = ['omit_share_urls']

# Instance-specific public contact and SMTP settings; passwords stay outside Git.
SUPPORT_EMAIL = os.getenv('REREVI_SUPPORT_EMAIL', 'support@example.org')
SOURCE_URL = os.getenv('REREVI_SOURCE_URL', 'https://github.com/mimo-567/rerevi-django')
SMTP_HOST = os.getenv('REREVI_SMTP_HOST', 'smtp.example.org')
SMTP_PORT = int(os.getenv('REREVI_SMTP_PORT', '465'))
SMTP_USERNAME = os.getenv('REREVI_SMTP_USERNAME', '')
SMTP_FROM = os.getenv('REREVI_SMTP_FROM', SUPPORT_EMAIL)
SMTP_OWNER = os.getenv('REREVI_SMTP_OWNER', '')
SMTP_SSL = os.getenv('REREVI_SMTP_SSL', 'true').lower() == 'true'
SMTP_TLS = os.getenv('REREVI_SMTP_TLS', 'false').lower() == 'true'
