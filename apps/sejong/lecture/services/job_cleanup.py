import logging

from apps.sejong.lecture.models import LectureDownloadJob

logger = logging.getLogger(__name__)


def delete_download_job(job: LectureDownloadJob) -> None:
    """다운로드 작업 이력을 삭제한다.

    완료된 파일이 파일시스템에 남아있다면 DB 레코드와 함께 삭제한다. 파일 삭제가
    실패해도 이력 삭제 자체는 계속 진행한다(고아 파일이 남는 것보다 이력이 지워지지
    않는 쪽이 더 나쁘다).
    """
    if job.file_relative_path:
        file_path = job.storage_root / job.file_relative_path
        try:
            file_path.unlink(missing_ok=True)
        except OSError as e:
            logger.error('강의 파일 삭제 실패 (job_id=%s): %s', job.id, e)
    job.delete()
