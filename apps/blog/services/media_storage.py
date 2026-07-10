"""블로그 글 작성 시 업로드되는 이미지·동영상·문서를 저장하는 서비스.

이미지는 압축 효율이 좋은 webp로 변환해 저장하고, 동영상·문서는 원본 그대로 저장한다.
"""
import logging
import re
import time
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable

import pillow_heif
from django.conf import settings
from django.core.files.base import ContentFile, File
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif'}
_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm'}
_DOCUMENT_EXTENSIONS = {'.pdf'}
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
    if extension in _VIDEO_EXTENSIONS:
        return _store(uploaded_file, extension, markdown_builder=_video_markdown)
    if extension in _DOCUMENT_EXTENSIONS:
        # 파일명에 [ ] 가 있으면 마크다운 링크 문법이 깨지므로 링크 텍스트에서만 제거한다.
        safe_name = uploaded_file.name.replace('[', '').replace(']', '')
        return _store(uploaded_file, extension, markdown_builder=lambda url: f'[{safe_name}]({url})')

    return MediaUploadResult(success=False, error_message=f'지원하지 않는 파일 형식입니다: {extension}')


def _save_image(uploaded_file: UploadedFile, extension: str) -> MediaUploadResult:
    try:
        image = Image.open(uploaded_file)
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        # DecompressionBombError는 OSError의 하위 클래스가 아니라서 별도로 잡아야 한다.
        # 픽셀 수가 MAX_IMAGE_PIXELS의 2배를 넘는 업로드(압축 폭탄)를 거부하기 위함.
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


def _video_markdown(url: str) -> str:
    return f'<video controls src="{url}"></video>'


_MEDIA_PATH_PATTERN = re.compile(re.escape(settings.MEDIA_URL) + r'(blog/uploads/[^\s\)"\']+)')


def extract_media_paths(content: str) -> list[str]:
    """본문에서 참조된 blog/uploads 하위 미디어 파일의 스토리지 상대 경로를 추출한다."""
    return _MEDIA_PATH_PATTERN.findall(content)


def delete_media_files(paths: list[str]) -> None:
    """주어진 스토리지 상대 경로의 파일들을 삭제한다. 개별 파일 삭제 실패는 로깅만 하고 계속 진행한다."""
    storage = FileSystemStorage()
    for path in paths:
        try:
            if storage.exists(path):
                storage.delete(path)
        except Exception as e:
            # OSError뿐 아니라 Django의 SuspiciousFileOperation(경로 검증 실패) 등도 포함해
            # 어떤 이유로든 파일 삭제가 실패해도 포스트 삭제·정리 커맨드 자체는 막지 않는다.
            logger.error('미디어 파일 삭제 실패: %s (%s)', path, e)


_UPLOAD_DIR = 'blog/uploads'


def find_orphaned_media(grace_seconds: int = 24 * 60 * 60) -> list[str]:
    """어떤 포스트에도 참조되지 않고, 수정 시각이 grace_seconds 이전인 blog/uploads 하위 파일의 스토리지 상대 경로를 반환한다."""
    from apps.blog.models import Post  # 이 함수를 쓰지 않는 다른 코드가 media_storage를 import할 때 불필요하게 Post를 로드하지 않도록 지연 import한다.

    referenced: set[str] = set()
    for content in Post.objects.values_list('content', flat=True):
        referenced.update(extract_media_paths(content))

    upload_dir = Path(settings.MEDIA_ROOT) / _UPLOAD_DIR
    if not upload_dir.exists():
        return []

    cutoff = time.time() - grace_seconds
    orphaned: list[str] = []
    for file_path in upload_dir.iterdir():
        if not file_path.is_file():
            continue
        relative_path = f'{_UPLOAD_DIR}/{file_path.name}'
        if relative_path in referenced:
            continue
        if file_path.stat().st_mtime > cutoff:
            continue
        orphaned.append(relative_path)
    return orphaned
