import pytest
from rest_framework.test import APIRequestFactory

from apps.blog.permissions import HasBlogIngestKey


@pytest.fixture
def factory() -> APIRequestFactory:
    return APIRequestFactory()


def test_올바른_키면_허용된다(factory: APIRequestFactory, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    request = factory.post('/api/v1/blog/ingest/', HTTP_X_BLOG_INGEST_KEY='secret-key')

    assert HasBlogIngestKey().has_permission(request, None) is True


def test_틀린_키면_거부된다(factory: APIRequestFactory, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    request = factory.post('/api/v1/blog/ingest/', HTTP_X_BLOG_INGEST_KEY='wrong-key')

    assert HasBlogIngestKey().has_permission(request, None) is False


def test_키가_없으면_거부된다(factory: APIRequestFactory, settings) -> None:
    settings.BLOG_INGEST_API_KEY = 'secret-key'
    request = factory.post('/api/v1/blog/ingest/')

    assert HasBlogIngestKey().has_permission(request, None) is False


def test_서버측_키가_비어있으면_어떤_키도_거부된다(factory: APIRequestFactory, settings) -> None:
    settings.BLOG_INGEST_API_KEY = ''
    request = factory.post('/api/v1/blog/ingest/', HTTP_X_BLOG_INGEST_KEY='')

    assert HasBlogIngestKey().has_permission(request, None) is False
