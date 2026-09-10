from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.sejong.lecture.models import LectureDownloadJob
from apps.sejong.lecture.services.job_cleanup import delete_download_job


@pytest.mark.django_db
def test_파일이_있으면_파일과_DB_레코드_모두_삭제(tmp_path) -> None:
    lectures_root = tmp_path / 'lectures'
    lectures_root.mkdir()
    file_path = lectures_root / '1.mp4'
    file_path.write_bytes(b'x')

    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='1', lecture_title='1주차',
        status=LectureDownloadJob.Status.COMPLETED, file_relative_path='1.mp4',
    )
    job_id = job.id

    with override_settings(MEDIA_ROOT=str(tmp_path / 'media')):
        delete_download_job(job)

    assert not file_path.exists()
    assert not LectureDownloadJob.objects.filter(pk=job_id).exists()


@pytest.mark.django_db
def test_파일경로가_없어도_DB_레코드는_삭제() -> None:
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='1', lecture_title='1주차',
        status=LectureDownloadJob.Status.FAILED,
    )
    job_id = job.id

    delete_download_job(job)

    assert not LectureDownloadJob.objects.filter(pk=job_id).exists()


@pytest.mark.django_db
def test_파일_삭제_실패해도_DB_레코드는_삭제(tmp_path) -> None:
    job = LectureDownloadJob.objects.create(
        course_id='101', course_name='자료구조', lecture_id='1', lecture_title='1주차',
        status=LectureDownloadJob.Status.COMPLETED, file_relative_path='1.mp4',
    )
    job_id = job.id

    with (
        override_settings(MEDIA_ROOT=str(tmp_path / 'media')),
        patch('pathlib.Path.unlink', side_effect=OSError('permission denied')),
    ):
        delete_download_job(job)

    assert not LectureDownloadJob.objects.filter(pk=job_id).exists()
