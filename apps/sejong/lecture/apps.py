import logging
import os
import sys

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class LectureConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sejong.lecture'
    label = 'lecture'
    verbose_name = '집현캠퍼스 강의'

    def ready(self) -> None:
        # 실제 서버 프로세스로 기동됐을 때만 정리 로직을 실행한다(허용리스트 방식).
        # Docker 빌드 타임의 `tailwind build`처럼 테이블이 아직 없는 management command
        # 실행 중 쿼리가 나가 빌드가 깨지는 문제와, 운영 중 임의 command 실행 시 진행
        # 중인 job을 실수로 FAILED로 덮어쓰는 문제를 함께 막는다.
        if not _should_run_orphan_cleanup():
            return
        # Django 개발 서버의 autoreload는 ready()를 2회 호출하므로 메인 프로세스에서만 실행한다.
        if settings.DEBUG and os.environ.get('RUN_MAIN') != 'true':
            return

        from apps.sejong.lecture.models import LectureDownloadJob

        updated_count = LectureDownloadJob.objects.filter(
            status__in=[LectureDownloadJob.Status.PENDING, LectureDownloadJob.Status.RUNNING],
        ).update(
            status=LectureDownloadJob.Status.FAILED,
            error_message='서버 재시작으로 중단됨',
        )
        if updated_count:
            logger.warning('서버 기동 시 고아 다운로드 작업 %d건을 FAILED로 정리했습니다.', updated_count)


def _should_run_orphan_cleanup() -> bool:
    """실제 서버 프로세스로 기동된 경우에만 True를 반환한다.

    `sys.argv[0]`이 `manage.py`로 끝나지 않으면(gunicorn/wsgi 등으로 기동된 실제 서버
    프로세스) 허용한다. `manage.py`로 끝나면 `runserver`(개발 서버)일 때만 허용하고,
    그 외 모든 management command(`tailwind`, `migrate`, `check`, `createsuperuser` 등
    무엇이든)는 건너뛴다.
    """
    if not sys.argv[0].endswith('manage.py'):
        return True
    return len(sys.argv) > 1 and sys.argv[1] == 'runserver'
