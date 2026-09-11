from unittest.mock import MagicMock, patch

import pytest

from apps.sejong.lecture.models import LectureDownloadJob
from apps.sejong.lecture.services.course import Course, Lecture
from apps.sejong.lecture.services.download_orchestrator import LectureDownloadOrchestrator
from apps.sejong.lecture.services.ecampus_auth import EcampusSession

_COURSE = Course(id='101', name='자료구조')
_LECTURE = Lecture(id='5001', title='1주차 강의')


@pytest.mark.django_db
def test_start_creates_pending_job_and_starts_background_thread() -> None:
    with patch('apps.sejong.lecture.services.download_orchestrator.threading.Thread') as mock_thread_cls:
        job = LectureDownloadOrchestrator().start(_COURSE, _LECTURE)

    assert job is not None
    assert job.status == LectureDownloadJob.Status.PENDING
    assert job.course_id == '101'
    assert job.course_name == '자료구조'
    assert job.lecture_id == '5001'
    assert job.lecture_title == '1주차 강의'

    mock_thread_cls.assert_called_once()
    _, kwargs = mock_thread_cls.call_args
    assert kwargs['args'] == (job.id,)
    assert kwargs['daemon'] is True
    mock_thread_cls.return_value.start.assert_called_once()


@pytest.mark.django_db
def test_start_truncates_course_name_and_lecture_title_to_field_limit() -> None:
    """Moodle에서 긁어온 이름/제목은 길이 제한이 없으므로, DB 컬럼(max_length=200)을
    넘겨 락 안에서 DataError가 나지 않도록 잘라서 저장해야 한다."""
    long_course = Course(id='101', name='자' * 250)
    long_lecture = Lecture(id='5001', title='주' * 250)

    with patch('apps.sejong.lecture.services.download_orchestrator.threading.Thread'):
        job = LectureDownloadOrchestrator().start(long_course, long_lecture)

    assert job is not None
    assert len(job.course_name) == 200
    assert len(job.lecture_title) == 200


@pytest.mark.django_db
def test_start_returns_none_when_job_already_pending() -> None:
    LectureDownloadJob.objects.create(
        course_id='999', course_name='이미 진행 중', lecture_id='1', lecture_title='기존 강의',
        status=LectureDownloadJob.Status.PENDING,
    )

    with patch('apps.sejong.lecture.services.download_orchestrator.threading.Thread'):
        job = LectureDownloadOrchestrator().start(_COURSE, _LECTURE)

    assert job is None


@pytest.mark.django_db
def test_start_returns_none_when_job_already_running() -> None:
    LectureDownloadJob.objects.create(
        course_id='999', course_name='이미 진행 중', lecture_id='1', lecture_title='기존 강의',
        status=LectureDownloadJob.Status.RUNNING,
    )

    with patch('apps.sejong.lecture.services.download_orchestrator.threading.Thread'):
        job = LectureDownloadOrchestrator().start(_COURSE, _LECTURE)

    assert job is None


@pytest.mark.django_db
def test_start_called_twice_second_call_returns_none() -> None:
    """동시에 두 번 start()를 호출하면 두 번째는 거부(None)되어야 한다."""
    with patch('apps.sejong.lecture.services.download_orchestrator.threading.Thread'):
        first_job = LectureDownloadOrchestrator().start(_COURSE, _LECTURE)
        second_job = LectureDownloadOrchestrator().start(_COURSE, _LECTURE)

    assert first_job is not None
    assert second_job is None
    assert LectureDownloadJob.objects.count() == 1


@pytest.mark.django_db
def test_run_success_marks_completed_and_sends_telegram_alert() -> None:
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.PENDING,
    )
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusMoodleAuthService.create_session',
            return_value=fake_session,
        ),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusCourseService.get_stream_url',
            return_value='https://cdn.example.com/token/index.m3u8',
        ),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.HlsDownloader.download_to_mp4',
        ) as mock_download,
        patch(
            'apps.sejong.lecture.services.download_orchestrator.TelegramService.send_admin_alert',
        ) as mock_alert,
        # 테스트 DB 커넥션은 pytest-django의 트랜잭션 격리에 쓰이므로 실제로 닫으면 안 된다 —
        # connection.close() 호출 자체는 test_run_closes_db_connection_in_finally에서 별도 검증한다.
        patch('apps.sejong.lecture.services.download_orchestrator.connection.close') as mock_close,
    ):
        LectureDownloadOrchestrator()._run(job.id)

    # ffmpeg 호출 전(idle 커넥션 방지)과 finally, 최소 2번은 close()가 불려야 한다.
    assert mock_close.call_count >= 2

    job.refresh_from_db()
    assert job.status == LectureDownloadJob.Status.COMPLETED
    assert job.file_relative_path == f'{job.id}.mp4'
    assert job.completed_at is not None
    mock_download.assert_called_once()
    mock_alert.assert_called_once()
    assert '완료' in mock_alert.call_args.args[0]


@pytest.mark.django_db
def test_run_marks_failed_when_login_fails() -> None:
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.PENDING,
    )

    with (
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusMoodleAuthService.create_session',
            return_value=None,
        ),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.TelegramService.send_admin_alert',
        ) as mock_alert,
        patch('apps.sejong.lecture.services.download_orchestrator.connection.close'),
    ):
        LectureDownloadOrchestrator()._run(job.id)

    job.refresh_from_db()
    assert job.status == LectureDownloadJob.Status.FAILED
    assert job.error_message == '집현캠퍼스 로그인에 실패했습니다.'
    mock_alert.assert_called_once()
    assert '실패' in mock_alert.call_args.args[0]


@pytest.mark.django_db
def test_run_marks_failed_when_stream_url_not_found() -> None:
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.PENDING,
    )
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusMoodleAuthService.create_session',
            return_value=fake_session,
        ),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusCourseService.get_stream_url',
            return_value=None,
        ),
        patch('apps.sejong.lecture.services.download_orchestrator.TelegramService.send_admin_alert'),
        patch('apps.sejong.lecture.services.download_orchestrator.connection.close'),
    ):
        LectureDownloadOrchestrator()._run(job.id)

    job.refresh_from_db()
    assert job.status == LectureDownloadJob.Status.FAILED
    assert job.error_message == '강의 스트림 URL을 찾을 수 없습니다.'


@pytest.mark.django_db
def test_run_marks_failed_when_downloader_raises_exception() -> None:
    """다운로드 도중 예외가 발생해도 스레드 안에서 삼켜지지 않고 status=FAILED로 기록되어야 한다."""
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.PENDING,
    )
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusMoodleAuthService.create_session',
            return_value=fake_session,
        ),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusCourseService.get_stream_url',
            return_value='https://cdn.example.com/token/index.m3u8',
        ),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.HlsDownloader.download_to_mp4',
            side_effect=RuntimeError('ffmpeg 실패'),
        ),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.TelegramService.send_admin_alert',
        ) as mock_alert,
        patch('apps.sejong.lecture.services.download_orchestrator.connection.close'),
    ):
        LectureDownloadOrchestrator()._run(job.id)

    job.refresh_from_db()
    assert job.status == LectureDownloadJob.Status.FAILED
    assert job.error_message == 'ffmpeg 실패'
    mock_alert.assert_called_once()


@pytest.mark.django_db
def test_run_success_keeps_completed_status_when_telegram_alert_raises() -> None:
    """텔레그램 발송이 예외를 던져도(예: 라이브러리 버그) 이미 완료된 작업 상태가
    FAILED로 뒤엎이면 안 된다 - 알림은 best-effort여야 한다."""
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.PENDING,
    )
    fake_session = EcampusSession(session=MagicMock())

    with (
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusMoodleAuthService.create_session',
            return_value=fake_session,
        ),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusCourseService.get_stream_url',
            return_value='https://cdn.example.com/token/index.m3u8',
        ),
        patch('apps.sejong.lecture.services.download_orchestrator.HlsDownloader.download_to_mp4'),
        patch(
            'apps.sejong.lecture.services.download_orchestrator.TelegramService.send_admin_alert',
            side_effect=RuntimeError('텔레그램 라이브러리 오류'),
        ),
        patch('apps.sejong.lecture.services.download_orchestrator.connection.close'),
    ):
        LectureDownloadOrchestrator()._run(job.id)

    job.refresh_from_db()
    assert job.status == LectureDownloadJob.Status.COMPLETED
    assert job.file_relative_path == job.output_filename


@pytest.mark.django_db
def test_run_closes_db_connection_in_finally() -> None:
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='5001', lecture_title='1주차 강의',
        status=LectureDownloadJob.Status.PENDING,
    )

    with (
        patch(
            'apps.sejong.lecture.services.download_orchestrator.EcampusMoodleAuthService.create_session',
            return_value=None,
        ),
        patch('apps.sejong.lecture.services.download_orchestrator.TelegramService.send_admin_alert'),
        # connection 객체 자체가 아니라 close 메서드만 모킹한다 — pytest-django는 트랜잭션
        # 격리를 위해 테스트 전체에서 동일한 물리 커넥션을 재사용하므로, 객체를 통째로 교체하거나
        # 실제로 close()를 실행하면 이후 테스트의 DB 접근이 깨진다.
        patch('apps.sejong.lecture.services.download_orchestrator.connection.close') as mock_close,
    ):
        LectureDownloadOrchestrator()._run(job.id)

    # close_old_connections()(시작 시 호출)도 커넥션 상태에 따라 내부적으로 close()를 호출할 수
    # 있어 정확한 호출 횟수는 환경에 따라 달라진다 — finally에서 close()가 최소 1회 호출됐는지만
    # (연결 정리가 누락되지 않았는지) 검증한다.
    assert mock_close.called
