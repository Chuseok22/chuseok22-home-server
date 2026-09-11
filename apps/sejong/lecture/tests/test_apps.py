from pathlib import Path
from unittest.mock import patch

import pytest

from apps.sejong.lecture.apps import LectureConfig, _should_run_orphan_cleanup
from apps.sejong.lecture.models import LectureDownloadJob


@pytest.mark.parametrize(
    ('argv', 'expected'),
    [
        (['/app/.venv/bin/gunicorn', 'config.wsgi:application'], True),
        (['manage.py', 'runserver'], True),
        (['manage.py', 'runserver', '0.0.0.0:8000'], True),
        (['manage.py', 'tailwind', 'build'], False),
        (['manage.py', 'tailwind', 'install'], False),
        (['manage.py', 'migrate'], False),
        (['manage.py', 'makemigrations'], False),
        (['manage.py', 'collectstatic'], False),
        (['manage.py', 'check'], False),
        (['manage.py', 'createsuperuser'], False),
        (['manage.py'], False),
    ],
)
def test_should_run_orphan_cleanup_uses_allowlist(argv: list[str], expected: bool) -> None:
    """Docker 빌드 타임의 `tailwind build`처럼 테이블이 없는 상태로 실행되는 임의의
    management command에서는 정리 로직이 실행되면 안 된다 — gunicorn(비-manage.py
    프로세스)과 `runserver`만 허용리스트에 포함한다."""
    with patch('apps.sejong.lecture.apps.sys.argv', argv):
        assert _should_run_orphan_cleanup() is expected


@pytest.mark.django_db
def test_ready_updates_orphan_jobs_when_running_as_gunicorn(settings) -> None:
    settings.DEBUG = False
    LectureDownloadJob.objects.create(
        course_id='1', course_name='c', lecture_id='1', lecture_title='l',
        status=LectureDownloadJob.Status.RUNNING,
    )

    with patch('apps.sejong.lecture.apps.sys.argv', ['/app/.venv/bin/gunicorn', 'config.wsgi:application']):
        LectureConfig('apps.sejong.lecture', __import__('apps.sejong.lecture', fromlist=['x'])).ready()

    job = LectureDownloadJob.objects.get()
    assert job.status == LectureDownloadJob.Status.FAILED
    assert job.error_message == '서버 재시작으로 중단됨'


@pytest.mark.django_db
def test_ready_removes_orphaned_part_files(settings, tmp_path: Path) -> None:
    """SIGKILL로 다운로드 도중 죽으면 downloader.py의 실패 핸들러가 실행되지 않아
    미완성 `<id>.mp4.part`가 영구 볼륨에 그대로 남는다 - 고아 job과 함께 지워야 한다."""
    settings.DEBUG = False
    settings.MEDIA_ROOT = tmp_path / 'output' / 'media'
    job = LectureDownloadJob.objects.create(
        course_id='1', course_name='c', lecture_id='1', lecture_title='l',
        status=LectureDownloadJob.Status.RUNNING,
    )
    part_path = job.storage_root / f'{job.output_filename}.part'
    part_path.parent.mkdir(parents=True, exist_ok=True)
    part_path.write_bytes(b'incomplete')

    with patch('apps.sejong.lecture.apps.sys.argv', ['/app/.venv/bin/gunicorn', 'config.wsgi:application']):
        LectureConfig('apps.sejong.lecture', __import__('apps.sejong.lecture', fromlist=['x'])).ready()

    assert not part_path.exists()


@pytest.mark.django_db
def test_ready_with_no_orphaned_jobs_is_a_noop(settings) -> None:
    """정리할 job이 없으면 조기 반환한다 - 예외 없이 끝나고 아무 것도 바뀌지 않아야 한다."""
    settings.DEBUG = False

    with patch('apps.sejong.lecture.apps.sys.argv', ['/app/.venv/bin/gunicorn', 'config.wsgi:application']):
        LectureConfig('apps.sejong.lecture', __import__('apps.sejong.lecture', fromlist=['x'])).ready()

    assert LectureDownloadJob.objects.count() == 0


@pytest.mark.django_db
def test_ready_does_not_query_db_during_tailwind_build(settings) -> None:
    """Dockerfile은 SECRET_KEY/DATABASE_URL만 더미로 채운 채 `tailwind build`를 빌드
    타임에 실행한다 — 이때 테이블이 없는 DB에 쿼리가 나가면 빌드 자체가 깨진다."""
    settings.DEBUG = False

    with (
        patch('apps.sejong.lecture.apps.sys.argv', ['manage.py', 'tailwind', 'build']),
        patch(
            'apps.sejong.lecture.models.LectureDownloadJob.objects',
        ) as mock_manager,
    ):
        LectureConfig('apps.sejong.lecture', __import__('apps.sejong.lecture', fromlist=['x'])).ready()

    mock_manager.filter.assert_not_called()


def test_ready_skips_on_dev_server_autoreload_subprocess(settings) -> None:
    """runserver는 허용리스트에 있지만, 개발 서버 autoreload의 최초(리로더) 프로세스에서는
    RUN_MAIN이 설정돼 있지 않으므로 실행하지 않는다(2회 호출 방지)."""
    settings.DEBUG = True

    with (
        patch('apps.sejong.lecture.apps.sys.argv', ['manage.py', 'runserver']),
        patch.dict('apps.sejong.lecture.apps.os.environ', {}, clear=False),
        patch(
            'apps.sejong.lecture.models.LectureDownloadJob.objects',
        ) as mock_manager,
    ):
        import os as os_module
        os_module.environ.pop('RUN_MAIN', None)
        LectureConfig('apps.sejong.lecture', __import__('apps.sejong.lecture', fromlist=['x'])).ready()

    mock_manager.filter.assert_not_called()
