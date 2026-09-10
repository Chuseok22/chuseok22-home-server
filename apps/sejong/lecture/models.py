from pathlib import Path

from django.conf import settings
from django.db import models


class LectureDownloadJob(models.Model):
    """강의 다운로드 작업 이력. 성공/실패 여부와 관계없이 모든 요청을 저장한다."""

    class Status(models.TextChoices):
        PENDING = 'pending', '대기'
        RUNNING = 'running', '진행중'
        COMPLETED = 'completed', '완료'
        FAILED = 'failed', '실패'

    course_id = models.CharField(max_length=20)
    course_name = models.CharField(max_length=200)
    lecture_id = models.CharField(max_length=20)
    lecture_title = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    # FileField를 쓰지 않는다 — MEDIA_ROOT는 config/urls.py에서 무인증으로 공개 서빙되므로
    # 강의 파일이 인증 없이 접근 가능한 공개 URL을 갖게 된다(Fable 5.1 검토로 발견).
    # 대신 MEDIA_ROOT 밖(같은 영구 볼륨인 output/lectures/)의 상대 경로만 저장하고,
    # 실제 파일 제공은 owner_required 뷰의 FileResponse로만 한다.
    file_relative_path = models.CharField(max_length=300, blank=True, default='')
    error_message = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lecture_download_job'
        ordering = ['-created_at']

    @property
    def storage_root(self) -> Path:
        """MEDIA_ROOT = BASE_DIR/'output'/'media' (공개 서빙) 와 형제 디렉터리 —
        같은 /app/output 영구 볼륨 안이지만 config/urls.py의 media/<path> 라우트가
        커버하지 않는 별도 경로이므로 인증 없이 접근되지 않는다.
        """
        return Path(settings.MEDIA_ROOT).parent / 'lectures'
