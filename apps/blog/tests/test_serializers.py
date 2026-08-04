from django.core.files.uploadedfile import SimpleUploadedFile

from apps.blog.serializers import BlogIngestImageUploadSerializer, BlogIngestSerializer


def test_필수_필드만_있어도_유효하다() -> None:
    serializer = BlogIngestSerializer(data={
        'title': '작업 회고',
        'content': '# 배경\n...',
        'category_name': 'waitee-app',
    })

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['summary'] == ''
    assert serializer.validated_data['tags'] == []
    assert serializer.validated_data['repo_url'] == ''


def test_title이_없으면_무효하다() -> None:
    serializer = BlogIngestSerializer(data={
        'content': '# 배경',
        'category_name': 'waitee-app',
    })

    assert not serializer.is_valid()
    assert 'title' in serializer.errors


def test_category_name이_없으면_무효하다() -> None:
    serializer = BlogIngestSerializer(data={
        'title': '작업 회고',
        'content': '# 배경',
    })

    assert not serializer.is_valid()
    assert 'category_name' in serializer.errors


def test_content가_상한을_초과하면_무효하다() -> None:
    serializer = BlogIngestSerializer(data={
        'title': '작업 회고',
        'content': 'x' * 50001,
        'category_name': 'waitee-app',
    })

    assert not serializer.is_valid()
    assert 'content' in serializer.errors


def test_모든_필드를_채우면_그대로_반영된다() -> None:
    serializer = BlogIngestSerializer(data={
        'title': '작업 회고',
        'summary': '요약',
        'content': '# 배경',
        'tags': ['django', 'api-design'],
        'category_name': 'waitee-app',
        'repo_url': 'https://github.com/example/waitee-app',
    })

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['tags'] == ['django', 'api-design']
    assert serializer.validated_data['repo_url'] == 'https://github.com/example/waitee-app'


def test_이미지_업로드_시리얼라이저는_파일_1개면_유효하다() -> None:
    upload = SimpleUploadedFile('photo.png', b'fake-image-bytes', content_type='image/png')

    serializer = BlogIngestImageUploadSerializer(data={'files': [upload]})

    assert serializer.is_valid(), serializer.errors
    assert len(serializer.validated_data['files']) == 1


def test_이미지_업로드_시리얼라이저는_파일이_없으면_무효하다() -> None:
    serializer = BlogIngestImageUploadSerializer(data={})

    assert not serializer.is_valid()
    assert 'files' in serializer.errors


def test_이미지_업로드_시리얼라이저는_10개_초과면_무효하다() -> None:
    uploads = [
        SimpleUploadedFile(f'photo{i}.png', b'fake-image-bytes', content_type='image/png')
        for i in range(11)
    ]

    serializer = BlogIngestImageUploadSerializer(data={'files': uploads})

    assert not serializer.is_valid()
    assert 'files' in serializer.errors


def test_이미지_업로드_시리얼라이저는_10개면_유효하다() -> None:
    uploads = [
        SimpleUploadedFile(f'photo{i}.png', b'fake-image-bytes', content_type='image/png')
        for i in range(10)
    ]

    serializer = BlogIngestImageUploadSerializer(data={'files': uploads})

    assert serializer.is_valid(), serializer.errors
    assert len(serializer.validated_data['files']) == 10
