import os
import time

import pytest
from django.core.management import call_command

from apps.blog.models import Post


def _touch_old(path, hours_ago: float) -> None:
    old_time = time.time() - hours_ago * 3600
    os.utime(path, (old_time, old_time))


@pytest.mark.django_db
def test_참조되지_않고_24시간_지난_파일은_삭제된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload_dir = tmp_path / 'blog' / 'uploads'
    upload_dir.mkdir(parents=True)
    orphan = upload_dir / 'orphan.webp'
    orphan.write_bytes(b'fake')
    _touch_old(orphan, hours_ago=25)

    call_command('cleanup_orphaned_media')

    assert not orphan.exists()


@pytest.mark.django_db
def test_참조된_파일은_삭제되지_않는다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload_dir = tmp_path / 'blog' / 'uploads'
    upload_dir.mkdir(parents=True)
    referenced = upload_dir / 'referenced.webp'
    referenced.write_bytes(b'fake')
    _touch_old(referenced, hours_ago=25)
    Post.objects.create(
        title='제목', slug='post-1',
        content='![이미지](/media/blog/uploads/referenced.webp)',
    )

    call_command('cleanup_orphaned_media')

    assert referenced.exists()


@pytest.mark.django_db
def test_24시간_이내_파일은_참조가_없어도_삭제되지_않는다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload_dir = tmp_path / 'blog' / 'uploads'
    upload_dir.mkdir(parents=True)
    recent = upload_dir / 'recent.webp'
    recent.write_bytes(b'fake')  # 방금 생성된 파일 — mtime을 건드리지 않음

    call_command('cleanup_orphaned_media')

    assert recent.exists()


@pytest.mark.django_db
def test_업로드_디렉터리가_없으면_안내_메시지만_출력한다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path

    call_command('cleanup_orphaned_media')  # 예외가 발생하지 않아야 한다
