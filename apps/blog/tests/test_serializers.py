from apps.blog.serializers import BlogIngestSerializer


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
