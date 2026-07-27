"""프로필 아바타 이미지 크롭 서비스.

관리자 페이지에서 업로드한 아바타를 지정된 좌표로 잘라 저장 가능한 형태로 변환한다.
"""
import logging
from dataclasses import dataclass
from io import BytesIO

import pillow_heif
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

_MAX_DIMENSION = 512


@dataclass(frozen=True)
class CropBox:
    """크롭할 영역. 원본 이미지 픽셀 좌표 기준이다."""

    x: int
    y: int
    width: int
    height: int


def crop_avatar(image_file: UploadedFile, crop_box: CropBox | None) -> ContentFile:
    """업로드된 아바타 이미지를 crop_box 영역으로 잘라 반환한다.

    crop_box가 없거나 이미지 범위를 벗어나면 원본 중앙 기준 정사각형으로 대체한다.
    """
    image = Image.open(image_file)
    image.load()
    image = ImageOps.exif_transpose(image)

    box = _resolve_box(image.width, image.height, crop_box)
    cropped = image.crop((box.x, box.y, box.x + box.width, box.y + box.height))

    if cropped.width > _MAX_DIMENSION:
        cropped = cropped.resize((_MAX_DIMENSION, _MAX_DIMENSION), Image.LANCZOS)

    has_alpha = cropped.mode in ('RGBA', 'LA') or (cropped.mode == 'P' and 'transparency' in cropped.info)
    cropped = cropped.convert('RGBA' if has_alpha else 'RGB')

    save_format = 'PNG' if has_alpha else 'JPEG'
    save_kwargs = {} if has_alpha else {'quality': 90}
    buffer = BytesIO()
    cropped.save(buffer, format=save_format, **save_kwargs)
    buffer.seek(0)

    extension = 'png' if has_alpha else 'jpg'
    return ContentFile(buffer.read(), name=f'avatar.{extension}')


def _resolve_box(image_width: int, image_height: int, crop_box: CropBox | None) -> CropBox:
    if crop_box is None:
        return _center_square(image_width, image_height)

    clamped = _clamp(image_width, image_height, crop_box)
    if clamped is None:
        logger.warning('아바타 크롭 좌표가 유효하지 않아 중앙 정사각형으로 대체합니다: %s', crop_box)
        return _center_square(image_width, image_height)
    return clamped


def _clamp(image_width: int, image_height: int, crop_box: CropBox) -> CropBox | None:
    """crop_box를 이미지 경계 안의 정사각형으로 클램프한다. 좌표 자체가 무효하면 None을 반환한다.

    좌표가 이미지 경계를 살짝 벗어나거나(예: 브라우저의 반올림 오차) 요청한 너비·높이가 서로 달라도
    크롭 자체를 포기하지 않고, 시작점(x, y)에서 이미지 경계 안에 들어가는 가장 큰 정사각형으로
    보정한다. 이렇게 하면 서버가 항상 1:1 비율을 보장하는 최종 source of truth가 된다.
    """
    if crop_box.width <= 0 or crop_box.height <= 0:
        return None
    if crop_box.x < 0 or crop_box.y < 0:
        return None

    max_side = min(image_width - crop_box.x, image_height - crop_box.y)
    if max_side <= 0:
        return None

    side = min(crop_box.width, crop_box.height, max_side)
    return CropBox(x=crop_box.x, y=crop_box.y, width=side, height=side)


def _center_square(image_width: int, image_height: int) -> CropBox:
    side = min(image_width, image_height)
    x = (image_width - side) // 2
    y = (image_height - side) // 2
    return CropBox(x=x, y=y, width=side, height=side)
