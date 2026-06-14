import logging
import os
import sys

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)

# 스케줄러를 기동하면 안 되는 management command 목록
# migrate 실행 시 django_apscheduler 테이블이 아직 존재하지 않아 오류 발생
_SKIP_SCHEDULER_COMMANDS = frozenset({
    'migrate', 'makemigrations', 'collectstatic',
    'check', 'shell', 'dbshell', 'spectacular',
})


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self) -> None:
        if not settings.ENABLE_SCHEDULER:
            return
        # management command 실행 중에는 스케줄러를 기동하지 않는다
        if len(sys.argv) > 1 and sys.argv[1] in _SKIP_SCHEDULER_COMMANDS:
            return
        # Django 개발 서버의 autoreload는 ready()를 2회 호출하므로 메인 프로세스에서만 기동한다
        if settings.DEBUG and os.environ.get('RUN_MAIN') != 'true':
            return
        from apps.core.scheduler import start_scheduler
        start_scheduler()
