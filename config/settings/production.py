from pathlib import Path
import environ

environ.Env.read_env(Path(__file__).resolve().parent.parent.parent / '.env.production')

from .base import *

DEBUG = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        # root가 WARNING이라 기본적으로 DEBUG 로그가 전부 버려짐 - 이슈 #152 재발 시
        # 토큰의 '+' 포함 여부를 로그만으로 판별하기 위한 진단 로그(sejong_auth.py)가
        # 실제로는 한 번도 기록되지 않던 문제를 막기 위해 이 모듈만 명시적으로 DEBUG 노출.
        'apps.sejong.library.services.sejong_auth': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
