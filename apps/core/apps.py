import logging
import os

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self) -> None:
        # ENABLE_SCHEDULER가 False면 management command(migrate 등) 실행 중이므로 스케줄러를 띄우지 않는다
        if not settings.ENABLE_SCHEDULER:
            return
        # Django 개발 서버의 autoreload는 ready()를 2회 호출하므로 메인 프로세스에서만 기동한다
        if settings.DEBUG and os.environ.get('RUN_MAIN') != 'true':
            return
        # import를 ready() 내부에 두어 앱 레지스트리 준비 전 모델 접근을 피한다
        from apps.core.scheduler import start_scheduler
        start_scheduler()
