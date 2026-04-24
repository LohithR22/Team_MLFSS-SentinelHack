"""
Django settings for SentinelHack — Oil Rig maintenance AI.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent  # Team_MLFSS-SentinelHack/

SECRET_KEY = 'django-insecure-dev-only-change-for-prod'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third-party
    'rest_framework',
    'corsheaders',
    'channels',

    # local
    'core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sentinel.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'sentinel.wsgi.application'
ASGI_APPLICATION = 'sentinel.asgi.application'

# --- Databases ---
# Default DB holds Django's own tables (users, sessions, admin) and our runtime
# state (work orders, events, stock/tool overlays). Team's read-only DBs live
# at the repo root and are attached as additional connections.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'runtime_state.db',
    },
    'fault_codes': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': REPO_ROOT / 'fault_codes.db',
        'OPTIONS': {'init_command': 'PRAGMA query_only = ON;'},
    },
    'sensor_data': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': REPO_ROOT / 'sensor_data.db',
        'OPTIONS': {'init_command': 'PRAGMA query_only = ON;'},
    },
    'technicians': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': REPO_ROOT / 'technicians.db',
        'OPTIONS': {'init_command': 'PRAGMA query_only = ON;'},
    },
}

# Paths to team artifacts
KB_DIR = REPO_ROOT / 'KB'
TOOL_IMAGES_DIR = REPO_ROOT / 'RigTools_Images'
ALERTS_DIR = REPO_ROOT / 'alerts'

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- DRF ---
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
}

# --- CORS (open during dev; frontend runs on 5173) ---
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True

# --- Channels (in-memory layer is fine for single-node demo) ---
CHANNEL_LAYERS = {
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
}

# --- Alert Agent ---
# When True (default), Alert Agent plays generated audio on the server's own
# speakers using afplay (macOS) / aplay (Linux). Rig-realistic PAGA behavior.
# Set False for headless deploys or silent testing.
SENTINEL_SERVER_AUTOPLAY = True
