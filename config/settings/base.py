from pathlib import Path
from datetime import timedelta
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'corsheaders',
    'django_apscheduler',
    'tailwind',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
]

LOCAL_APPS = [
    'apps.core',
    'apps.notifications',
    'apps.sejong.library',
    'apps.activity',
    'apps.projects',
    'apps.sejong.student',
    'apps.blog',
    'theme',
    'apps.accounts',
    'apps.site',
    'apps.engagement',
    'apps.ai',
]

TAILWIND_APP_NAME = 'theme'

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

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
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL')
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'output' / 'media'  # /app/output 전체가 배포 시 영구 볼륨에 마운트되며, 미디어 외 다른 산출물도 이 아래에 추가될 수 있다

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_RATES': {
        'blog_ingest': '30/day',
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'chuseok22-home-server API',
    'DESCRIPTION': 'chuseok22-home-server REST API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
    },
}

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# 텔레그램 알림 설정
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_ADMIN_CHAT_ID = env('TELEGRAM_ADMIN_CHAT_ID', default='')

# 세종대 포털 인증 설정
SEJONG_STUDENT_ID = env('SEJONG_STUDENT_ID', default='')
SEJONG_PASSWORD = env('SEJONG_PASSWORD', default='')
# classic.sejong.ac.kr SSO 콜백 경로 — 브라우저 DevTools로 확인 후 .env에서 재정의 가능
SEJONG_CLASSIC_SSO_CALLBACK_PATH = env('SEJONG_CLASSIC_SSO_CALLBACK_PATH', default='/_custom/sejong/sso/sso-return.jsp')

# GitHub 활동 수집 설정
GITHUB_PAT = env('GITHUB_PAT', default='')
GITHUB_USERNAME = env('GITHUB_USERNAME', default='')

# 스케줄러 설정 (django-apscheduler)
# ENABLE_SCHEDULER: management command(migrate 등) 실행 시 스케줄러 기동을 막기 위한 게이트
ENABLE_SCHEDULER = env.bool('ENABLE_SCHEDULER', default=False)
APSCHEDULER_DATETIME_FORMAT = 'N j, Y, f:s a'
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # 초

# GitHub OAuth 소셜 로그인
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'APP': {
            'client_id': env('GITHUB_OAUTH_CLIENT_ID', default=''),
            'secret': env('GITHUB_OAUTH_CLIENT_SECRET', default=''),
        },
    },
}
ACCOUNT_EMAIL_VERIFICATION = 'none'
LOGIN_REDIRECT_URL = '/'

# 자체 이메일/비밀번호 회원가입 차단 (GitHub OAuth 소셜 로그인만 허용)
ACCOUNT_ADAPTER = 'apps.accounts.adapters.NoLocalSignupAccountAdapter'
# ACCOUNT_ADAPTER의 is_open_for_signup=False가 소셜 로그인 신규가입까지 막는 것을 방지
SOCIALACCOUNT_ADAPTER = 'apps.accounts.adapters.AllowSocialSignupAdapter'

# 사이트 소유자로 자동 승격할 GitHub 숫자 사용자 ID (username이 아님 — 개명·재등록에 영향받지 않음)
GITHUB_OWNER_ID = env('GITHUB_OWNER_ID', default='')

# 블로그 자동 포스팅(ingest) 전용 API 키 — 기존 JWT 로그인과 분리된 별도 인증
BLOG_INGEST_API_KEY = env('BLOG_INGEST_API_KEY', default='')

# SUH-AIder AI 서버 연동 설정
SUH_AIDER_BASE_URL = env('SUH_AIDER_BASE_URL', default='')
SUH_AIDER_API_KEY = env('SUH_AIDER_API_KEY', default='')
