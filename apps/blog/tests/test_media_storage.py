import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.blog.services.media_storage import save_uploaded_media


def _make_image_upload(
    name: str, image_format: str, mode: str = 'RGB', size: tuple[int, int] = (10, 10),
) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new(mode, size, color='red').save(buffer, format=image_format)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type=f'image/{image_format.lower()}')


def test_png_이미지_업로드시_webp로_변환되어_저장된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload = _make_image_upload('photo.png', 'PNG')

    result = save_uploaded_media(upload)

    assert result.success is True
    assert result.url.endswith('.webp')
    assert result.markdown == f'![업로드 이미지]({result.url})'
    assert list(tmp_path.rglob('*.webp'))


def test_투명_배경_png는_rgba로_유지되어_webp로_저장된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    buffer = io.BytesIO()
    # 실제로 투명한 픽셀(alpha=0)이어야 webp 저장 시 알파 채널이 보존된다.
    # 완전 불투명(alpha=255)이면 libwebp가 중복 알파 평면을 제거해 RGB로 저장되므로,
    # 이 테스트가 검증하려는 "투명 배경 보존"을 실제로 재현하려면 alpha=0 픽셀이 필요하다.
    Image.new('RGBA', (10, 10), color=(255, 0, 0, 0)).save(buffer, format='PNG')
    buffer.seek(0)
    upload = SimpleUploadedFile('transparent.png', buffer.read(), content_type='image/png')

    result = save_uploaded_media(upload)

    assert result.success is True
    saved_path = next(tmp_path.rglob('*.webp'))
    with Image.open(saved_path) as saved_image:
        assert saved_image.mode == 'RGBA'


def test_애니메이션_gif는_변환하지_않고_원본_그대로_저장된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    frame_1 = Image.new('RGB', (10, 10), color='red')
    frame_2 = Image.new('RGB', (10, 10), color='blue')
    buffer = io.BytesIO()
    frame_1.save(buffer, format='GIF', save_all=True, append_images=[frame_2])
    buffer.seek(0)
    upload = SimpleUploadedFile('anim.gif', buffer.read(), content_type='image/gif')

    result = save_uploaded_media(upload)

    assert result.success is True
    assert result.url.endswith('.gif')


def test_exif_회전_정보가_적용되어_저장된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    image = Image.new('RGB', (20, 10), color='red')
    exif = image.getexif()
    exif[0x0112] = 6  # Orientation: 세로로 촬영된 폰 사진에 흔한 값
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', exif=exif)
    buffer.seek(0)
    upload = SimpleUploadedFile('rotated.jpg', buffer.read(), content_type='image/jpeg')

    result = save_uploaded_media(upload)

    assert result.success is True
    saved_path = next(tmp_path.rglob('*.webp'))
    with Image.open(saved_path) as saved_image:
        assert saved_image.size == (10, 20)


def test_손상된_이미지_파일은_거부된다() -> None:
    upload = SimpleUploadedFile('broken.png', b'not-a-real-image-content', content_type='image/png')

    result = save_uploaded_media(upload)

    assert result.success is False
    assert '이미지' in result.error_message


def test_50mb_초과_파일은_거부된다() -> None:
    oversized = SimpleUploadedFile('big.png', b'0' * (50 * 1024 * 1024 + 1), content_type='image/png')

    result = save_uploaded_media(oversized)

    assert result.success is False
    assert '50MB' in result.error_message


def test_지원하지_않는_확장자는_거부된다() -> None:
    upload = SimpleUploadedFile('archive.zip', b'dummy', content_type='application/zip')

    result = save_uploaded_media(upload)

    assert result.success is False
    assert '지원하지 않는' in result.error_message


def test_heic_이미지_업로드시_webp로_변환되어_저장된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    import pillow_heif

    pil_image = Image.new('RGB', (10, 10), color='blue')
    heif_file = pillow_heif.from_pillow(pil_image)
    buffer = io.BytesIO()
    heif_file.save(buffer, format='HEIF')
    buffer.seek(0)
    upload = SimpleUploadedFile('photo.heic', buffer.read(), content_type='image/heic')

    result = save_uploaded_media(upload)

    assert result.success is True
    assert result.url.endswith('.webp')


def test_mp4_동영상은_원본_그대로_저장되고_video_태그가_생성된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload = SimpleUploadedFile('clip.mp4', b'fake-video-bytes', content_type='video/mp4')

    result = save_uploaded_media(upload)

    assert result.success is True
    assert result.url.endswith('.mp4')
    assert result.markdown == f'<video controls src="{result.url}"></video>'


def test_pdf_문서는_원본_그대로_저장되고_링크가_생성된다(settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    upload = SimpleUploadedFile('resume.pdf', b'%PDF-1.4 fake', content_type='application/pdf')

    result = save_uploaded_media(upload)

    assert result.success is True
    assert result.url.endswith('.pdf')
    assert result.markdown == f'[resume.pdf]({result.url})'
