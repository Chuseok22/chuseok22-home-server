import pytest

from apps.blog.models import Post


@pytest.mark.django_db
def test_포스트_삭제시_참조된_미디어_파일이_삭제된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload_dir = tmp_path / 'blog' / 'uploads'
    upload_dir.mkdir(parents=True)
    image_path = upload_dir / 'a.webp'
    image_path.write_bytes(b'fake')

    post = Post.objects.create(
        title='제목', slug='post-with-media',
        content='![이미지](/media/blog/uploads/a.webp)',
    )

    post.delete()

    assert not image_path.exists()


@pytest.mark.django_db
def test_대량_삭제에도_참조된_미디어_파일이_삭제된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload_dir = tmp_path / 'blog' / 'uploads'
    upload_dir.mkdir(parents=True)
    image_path = upload_dir / 'b.webp'
    image_path.write_bytes(b'fake')

    Post.objects.create(
        title='제목', slug='post-bulk-delete',
        content='![이미지](/media/blog/uploads/b.webp)',
    )

    Post.objects.filter(slug='post-bulk-delete').delete()

    assert not image_path.exists()


@pytest.mark.django_db
def test_본문에_미디어_참조가_없으면_삭제_시도조차_하지_않는다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path

    post = Post.objects.create(title='제목', slug='post-no-media', content='텍스트만 있음')

    post.delete()  # 예외가 발생하지 않아야 한다
