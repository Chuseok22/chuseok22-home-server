from django.http import HttpRequest
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.blog.models import Post
from apps.blog.permissions import HasBlogIngestKey
from apps.blog.serializers import BlogIngestSerializer
from apps.blog.services.category import get_or_create_dev_category
from apps.blog.services.slug import generate_unique_slug


class BlogIngestView(APIView):
    """외부 프로젝트 작업 결과를 블로그 초안으로 등록하는 ingest 전용 엔드포인트."""

    authentication_classes: list = []
    permission_classes = [HasBlogIngestKey]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'blog_ingest'

    @extend_schema(
        summary='블로그 글 자동 등록 (Ingest)',
        description=(
            '외부 프로젝트에서 작업 결과를 블로그 초안으로 등록한다. '
            '`X-Blog-Ingest-Key` 헤더의 전용 API 키로만 인증하며(JWT 미사용), '
            '항상 초안(`is_published=False`) 상태로 생성된다. '
            '`category_name`으로 넘긴 값은 "개발" 대분류 아래 소분류로 자동 생성(get_or_create)된다.'
        ),
        request=BlogIngestSerializer,
        responses={
            201: OpenApiResponse(description='초안 생성 성공'),
            400: OpenApiResponse(description='입력 검증 오류'),
            403: OpenApiResponse(description='API 키 누락 또는 불일치'),
        },
        tags=['blog'],
    )
    def post(self, request: HttpRequest) -> Response:
        serializer = BlogIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        category = get_or_create_dev_category(data['category_name'])
        post = Post.objects.create(
            title=data['title'],
            slug=generate_unique_slug(Post, data['title']),
            summary=data['summary'],
            content=data['content'],
            tags=data['tags'],
            category=category,
            repo_url=data['repo_url'],
            is_published=False,
        )

        return Response(
            {
                'id': post.id,
                'slug': post.slug,
                'admin_url': f'/admin/blog/post/{post.id}/change/',
            },
            status=201,
        )
