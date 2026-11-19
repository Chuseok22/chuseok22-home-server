from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.site.services.card_image import resize_card_image


def _upload(width: int, height: int, mode: str = 'RGB', image_format: str = 'PNG') -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new(mode, (width, height), 'white').save(buffer, format=image_format)
    return SimpleUploadedFile('card.png', buffer.getvalue(), content_type='image/png')


def _open(result) -> Image.Image:
    result.seek(0)
    image = Image.open(BytesIO(result.read()))
    image.load()
    return image


def test_resize_card_image는_넓은_이미지를_가로_1200px로_비율을_유지하며_줄인다() -> None:
    image = _open(resize_card_image(_upload(2400, 1300)))

    assert image.size == (1200, 650)


def test_resize_card_image는_작은_이미지를_확대하지_않는다() -> None:
    image = _open(resize_card_image(_upload(600, 330)))

    assert image.size == (600, 330)


def test_resize_card_image는_투명_이미지를_png로_유지한다() -> None:
    result = resize_card_image(_upload(800, 400, mode='RGBA'))

    assert _open(result).format == 'PNG'
    assert result.name.endswith('.png')


def test_resize_card_image는_불투명_이미지를_jpeg로_변환한다() -> None:
    result = resize_card_image(_upload(800, 400))

    assert _open(result).format == 'JPEG'
    assert result.name.endswith('.jpg')


def test_resize_card_image는_이미지가_아닌_파일이면_원본을_그대로_반환한다() -> None:
    broken = SimpleUploadedFile('card.png', b'not an image', content_type='image/png')

    result = resize_card_image(broken)

    assert result.read() == b'not an image'
