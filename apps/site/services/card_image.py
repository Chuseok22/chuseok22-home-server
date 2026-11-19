"""명함 이미지 리사이즈 서비스.

Admin에서 올린 명함 이미지를 비율은 유지한 채 가로 최대 1200px로 줄여 저장 가능한 형태로 변환한다.
"""
import logging
from io import BytesIO

import pillow_heif
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

pillow_heif.register_heif_opener()

logger = logging.getLogger(__name__)

_MAX_WIDTH = 1200


def resize_card_image(image_file: UploadedFile) -> ContentFile:
    """업로드된 명함 이미지를 가로 최대 1200px로 줄여 반환한다. 작은 이미지는 확대하지 않는다.

    투명도가 있으면 PNG, 없으면 JPEG로 저장한다. 디코드에 실패하면 줄이기를 포기하고 원본을 그대로 반환한다.
    """
    try:
        image = Image.open(image_file)
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        # DecompressionBombError는 OSError의 하위 클래스가 아니라서 별도로 잡아야 한다.
        logger.error('명함 이미지 디코드 실패, 리사이즈 없이 원본을 저장합니다: %s', error)
        image_file.seek(0)
        return ContentFile(image_file.read(), name=image_file.name)

    image = ImageOps.exif_transpose(image)
    if image.width > _MAX_WIDTH:
        height = round(image.height * _MAX_WIDTH / image.width)
        image = image.resize((_MAX_WIDTH, height), Image.LANCZOS)

    has_alpha = image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info)
    image = image.convert('RGBA' if has_alpha else 'RGB')

    save_format = 'PNG' if has_alpha else 'JPEG'
    save_kwargs = {} if has_alpha else {'quality': 90}
    buffer = BytesIO()
    image.save(buffer, format=save_format, **save_kwargs)

    extension = 'png' if has_alpha else 'jpg'
    return ContentFile(buffer.getvalue(), name=f'card.{extension}')
