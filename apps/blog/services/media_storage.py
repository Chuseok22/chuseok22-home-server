"""블로그 글 작성 시 업로드되는 이미지·동영상·문서를 저장하는 서비스.

이미지는 압축 효율이 좋은 webp로 변환해 저장하고, 동영상·문서는 원본 그대로 저장한다.
"""
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable

import pillow_heif
from django.core.files.base import ContentFile, File
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

pillow_heif.register_heif_opener()

_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif'}
_MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
_WEBP_QUALITY = 82


@dataclass(frozen=True)
class MediaUploadResult:
    """미디어 업로드 처리 결과. 실패 시 error_message만 채워진다."""

    success: bool
    url: str = ''
    markdown: str = ''
    error_message: str = ''


def save_uploaded_media(uploaded_file: UploadedFile) -> MediaUploadResult:
    """업로드된 파일을 저장하고 본문에 삽입할 마크다운 스니펫을 반환한다."""
    if uploaded_file.size > _MAX_UPLOAD_SIZE:
        return MediaUploadResult(success=False, error_message='파일 크기는 50MB를 초과할 수 없습니다.')

    extension = Path(uploaded_file.name).suffix.lower()

    if extension in _IMAGE_EXTENSIONS:
        return _save_image(uploaded_file, extension)

    return MediaUploadResult(success=False, error_message=f'지원하지 않는 파일 형식입니다: {extension}')


def _save_image(uploaded_file: UploadedFile, extension: str) -> MediaUploadResult:
    try:
        image = Image.open(uploaded_file)
        image.load()
    except (UnidentifiedImageError, OSError):
        return MediaUploadResult(success=False, error_message='올바른 이미지 파일이 아닙니다.')

    if getattr(image, 'is_animated', False):
        # 움직이는 GIF 등은 webp 변환 시 첫 프레임만 남으므로 원본을 그대로 저장한다.
        uploaded_file.seek(0)
        return _store(uploaded_file, extension, markdown_builder=_image_markdown)

    # 폰으로 세로로 찍은 사진은 EXIF Orientation 태그로만 회전 정보를 가지고 있는 경우가 많다.
    # webp로 재인코딩하면서 EXIF가 사라지므로, 저장 전에 실제 픽셀을 회전시켜 반영해야 한다.
    image = ImageOps.exif_transpose(image)

    has_alpha = image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info)
    image = image.convert('RGBA' if has_alpha else 'RGB')

    buffer = BytesIO()
    image.save(buffer, format='WEBP', quality=_WEBP_QUALITY)
    buffer.seek(0)

    return _store(ContentFile(buffer.read()), '.webp', markdown_builder=_image_markdown)


def _store(file_content: File, extension: str, markdown_builder: Callable[[str], str]) -> MediaUploadResult:
    name = f'blog/uploads/{uuid.uuid4().hex}{extension}'
    storage = FileSystemStorage()
    saved_name = storage.save(name, file_content)
    url = storage.url(saved_name)
    return MediaUploadResult(success=True, url=url, markdown=markdown_builder(url))


def _image_markdown(url: str) -> str:
    return f'![업로드 이미지]({url})'
