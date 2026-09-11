import logging
import threading
from typing import ClassVar

from django.db import close_old_connections, connection
from django.utils import timezone

from apps.notifications.services.telegram import TelegramService
from apps.sejong.lecture.models import LectureDownloadJob
from apps.sejong.lecture.services.course import Course, EcampusCourseService, Lecture
from apps.sejong.lecture.services.downloader import HlsDownloader, _mask_urls_in_text
from apps.sejong.lecture.services.ecampus_auth import EcampusMoodleAuthService

logger = logging.getLogger(__name__)

_ERROR_MESSAGE_MAX_LENGTH = 500


class LectureDownloadOrchestrator:
    """강의 다운로드 요청을 백그라운드 스레드로 실행하고 진행 상태를 기록하는 오케스트레이터.

    Gunicorn `--workers 1`(단일 프로세스) 배포를 전제로, 클래스 레벨 락으로 동시에 1건만
    실행되도록 제한한다(apps.sejong.library.services.sejong_auth.SejongLibraryAuthService의
    `_lock` 사용법과 동일 패턴).
    """

    _lock: ClassVar[threading.Lock] = threading.Lock()

    def start(self, course: Course, lecture: Lecture) -> LectureDownloadJob | None:
        """다운로드 작업을 생성하고 백그라운드 스레드로 실행을 시작한다.

        이미 대기(PENDING) 또는 진행중(RUNNING)인 작업이 있으면 새 요청을 거부하고 None을
        반환한다. "존재 확인"과 "생성"을 같은 락 블록 안에서 원자적으로 수행해야
        check-then-create 경합(동시 요청 시 2건 이상 실행)을 막을 수 있다.
        """
        with LectureDownloadOrchestrator._lock:
            has_active_job = LectureDownloadJob.objects.filter(
                status__in=[LectureDownloadJob.Status.PENDING, LectureDownloadJob.Status.RUNNING],
            ).exists()
            if has_active_job:
                logger.warning('이미 진행 중인 다운로드 작업이 있어 요청을 거부합니다.')
                return None

            job = LectureDownloadJob.objects.create(
                course_id=course.id,
                # Moodle에서 긁어온 이름/제목은 길이 제한이 없으므로, 모델 필드 max_length를
                # 초과해 DataError로 락 안에서 요청이 죽는 일이 없도록 여기서 잘라둔다.
                course_name=course.name[:200],
                lecture_id=lecture.id,
                lecture_title=lecture.title[:200],
                status=LectureDownloadJob.Status.PENDING,
            )

        threading.Thread(target=self._run, args=(job.id,), daemon=True).start()
        return job

    def _run(self, job_id: int) -> None:
        """백그라운드 스레드에서 실제 다운로드를 수행한다.

        스레드 내부 예외는 스레드만 종료시킬 뿐 어디에도 전파되지 않으므로, 어떤 예외든
        반드시 status=FAILED로 기록해야 한다(그렇지 않으면 작업이 RUNNING 상태로 영구히
        멈춘 것처럼 보인다). Django DB 커넥션은 스레드 로컬이라 스레드 종료 시 자동으로
        닫히지 않으므로 finally에서 connection.close()를 호출한다.
        """
        close_old_connections()
        try:
            job = LectureDownloadJob.objects.get(id=job_id)
            try:
                self._download(job)
            except Exception as e:
                # ffmpeg 관련 예외(subprocess.CalledProcessError/TimeoutExpired)의 str()에는
                # ffmpeg 커맨드 전체(m3u8 URL의 인증 토큰 포함)가 그대로 들어있을 수 있어
                # DB/로그/텔레그램에 남기기 전에 반드시 마스킹한다.
                self._mark_failed(job, _mask_urls_in_text(str(e)))
        finally:
            connection.close()

    def _download(self, job: LectureDownloadJob) -> None:
        job.status = LectureDownloadJob.Status.RUNNING
        job.save(update_fields=['status'])

        # EcampusCourseService가 내부적으로 로그인/세션 만료 재인증까지 처리하므로 여기서는
        # 완전한 로그인 실패(캐시도 재로그인도 실패)만 조기에 구분해 명확한 메시지로 남긴다.
        ecampus_session = EcampusMoodleAuthService().create_session()
        if ecampus_session is None:
            self._mark_failed(job, '집현캠퍼스 로그인에 실패했습니다.')
            return

        # CDN URL 토큰의 TTL이 짧을 수 있으므로 다운로드 시작 직전에 매번 새로 조회한다(캐시 금지).
        stream_url = EcampusCourseService().get_stream_url(job.lecture_id)
        if stream_url is None:
            self._mark_failed(job, '강의 스트림 URL을 찾을 수 없습니다.')
            return

        # ffmpeg는 최대 _FFMPEG_TIMEOUT_SECONDS(2시간) 동안 실행될 수 있어, 그 사이 이
        # 커넥션이 idle 상태로 방치되면 DB/네트워크 타임아웃으로 끊길 수 있다. 여기서
        # 닫아두면 이후 첫 ORM 호출(job.save())에서 Django가 새 커넥션을 lazy하게 연다.
        connection.close()

        relative_path = job.output_filename
        output_path = job.storage_root / relative_path
        HlsDownloader().download_to_mp4(stream_url, output_path)

        job.status = LectureDownloadJob.Status.COMPLETED
        job.file_relative_path = relative_path
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'file_relative_path', 'completed_at'])
        self._notify(f'✅ {job.lecture_title} 다운로드 완료')

    def _mark_failed(self, job: LectureDownloadJob, reason: str) -> None:
        error_message = reason[:_ERROR_MESSAGE_MAX_LENGTH]
        job.status = LectureDownloadJob.Status.FAILED
        job.error_message = error_message
        job.save(update_fields=['status', 'error_message'])
        logger.error('강의 다운로드 실패 (job_id=%s): %s', job.id, error_message)
        self._notify(f'❌ {job.lecture_title} 다운로드 실패: {error_message}')

    @staticmethod
    def _notify(message: str) -> None:
        """텔레그램 알림은 best-effort로만 시도한다 - 발송 실패가 이미 저장된 작업
        상태(완료/실패)를 뒤엎으면 안 되므로 예외를 여기서 흡수하고 기록만 한다."""
        try:
            TelegramService().send_admin_alert(message)
        except Exception as e:
            logger.error('텔레그램 알림 발송 중 예외 발생(작업 상태에는 영향 없음): %s', e)
