from django.conf import settings
from django.http import HttpRequest
from django.utils.crypto import constant_time_compare
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView


class HasBlogIngestKey(BasePermission):
    """블로그 ingest 전용 API 키 인증. 기존 JWT 로그인 흐름과 완전히 분리된 권한이다."""

    def has_permission(self, request: HttpRequest, view: APIView) -> bool:
        expected = settings.BLOG_INGEST_API_KEY
        if not expected:
            return False
        key = request.headers.get('X-Blog-Ingest-Key', '')
        return constant_time_compare(key, expected)
