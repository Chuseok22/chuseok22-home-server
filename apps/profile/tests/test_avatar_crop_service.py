import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.profile.services.avatar_crop import CropBox, crop_avatar


def _make_upload(name: str, size: tuple[int, int], color: str = 'red') -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new('RGB', size, color=color).save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/png')


def test_지정한_좌표대로_크롭된다() -> None:
    # 왼쪽 절반은 빨강, 오른쪽 절반은 파랑인 100x50 RGBA 이미지를 만든다. 알파 채널이 있으면
    # crop_avatar가 무손실 PNG로 저장하므로(JPEG였다면 손실 압축으로 픽셀 값이 ±1 어긋날 수 있어
    # 아래의 정확한 픽셀 비교가 흔들릴 수 있다), 정확한 픽셀 값 비교가 가능하다.
    image = Image.new('RGBA', (100, 50), color=(255, 0, 0, 255))
    for x in range(50, 100):
        for y in range(50):
            image.putpixel((x, y), (0, 0, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    upload = SimpleUploadedFile('half.png', buffer.read(), content_type='image/png')

    result = crop_avatar(upload, CropBox(x=50, y=0, width=50, height=50))

    cropped = Image.open(result)
    assert cropped.size == (50, 50)
    assert cropped.getpixel((25, 25)) == (0, 0, 255, 255)


def test_크롭_좌표가_없으면_중앙_정사각형으로_대체된다() -> None:
    upload = _make_upload('wide.png', (100, 50))

    result = crop_avatar(upload, None)

    cropped = Image.open(result)
    assert cropped.size == (50, 50)


def test_범위를_벗어난_좌표는_경계에_맞춰_클램프된다() -> None:
    # 100x50 이미지에서 x=90부터 폭 50을 요청하면 오른쪽 경계(100)까지 남은 폭은 10뿐이다.
    # 크롭 자체를 포기하고 중앙 정사각형으로 대체하는 대신, 요청 의도를 최대한 살려 경계 안에서
    # 가능한 가장 큰 정사각형(10x10)으로 클램프한다. 브라우저가 계산한 좌표가 반올림 때문에
    # 원본 경계를 1px 넘는 경우에도 사용자의 크롭 지정이 통째로 무시되지 않도록 하기 위함이다.
    upload = _make_upload('small.png', (100, 50))

    result = crop_avatar(upload, CropBox(x=90, y=0, width=50, height=50))

    cropped = Image.open(result)
    assert cropped.size == (10, 10)


def test_음수_좌표는_중앙_정사각형으로_대체된다() -> None:
    upload = _make_upload('negative.png', (100, 50))

    result = crop_avatar(upload, CropBox(x=-5, y=0, width=50, height=50))

    cropped = Image.open(result)
    assert cropped.size == (50, 50)


def test_크롭_박스_크기가_0_이하면_중앙_정사각형으로_대체된다() -> None:
    upload = _make_upload('zero.png', (100, 50))

    result = crop_avatar(upload, CropBox(x=10, y=10, width=0, height=0))

    cropped = Image.open(result)
    assert cropped.size == (50, 50)


def test_직사각형_좌표는_짧은_변에_맞춰_정사각형으로_클램프된다() -> None:
    # 서버가 1:1 비율을 강제하는지 검증한다 — 클라이언트 JS가 정상 동작하면 발생하지 않아야 하지만,
    # 서버가 source of truth이므로 비정사각 좌표가 들어와도 항상 정사각형 결과를 보장해야 한다.
    upload = _make_upload('rect.png', (100, 50))

    result = crop_avatar(upload, CropBox(x=0, y=0, width=80, height=40))

    cropped = Image.open(result)
    assert cropped.size == (40, 40)


def test_512px보다_큰_크롭_결과는_512로_축소된다() -> None:
    upload = _make_upload('large.png', (1000, 1000))

    result = crop_avatar(upload, CropBox(x=0, y=0, width=1000, height=1000))

    cropped = Image.open(result)
    assert cropped.size == (512, 512)


def test_heic_이미지도_크롭된다() -> None:
    import pillow_heif

    pil_image = Image.new('RGB', (100, 100), color='blue')
    heif_file = pillow_heif.from_pillow(pil_image)
    buffer = io.BytesIO()
    heif_file.save(buffer, format='HEIF')
    buffer.seek(0)
    upload = SimpleUploadedFile('photo.heic', buffer.read(), content_type='image/heic')

    result = crop_avatar(upload, CropBox(x=0, y=0, width=50, height=50))

    cropped = Image.open(result)
    assert cropped.size == (50, 50)
