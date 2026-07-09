from typing import ClassVar

from django.urls import reverse
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.blog.models import Category, Post
from apps.blog.permissions import HasBlogIngestKey
from apps.blog.serializers import BlogIngestSerializer, CategoryListSerializer
from apps.blog.services.category import CategoryNotFoundError, get_category_by_name
from apps.blog.services.slug import generate_unique_slug


class BlogIngestView(APIView):
    """외부 프로젝트 작업 결과를 블로그 초안으로 등록하는 ingest 전용 엔드포인트."""

    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = [HasBlogIngestKey]
    throttle_classes: ClassVar[list] = [ScopedRateThrottle]
    throttle_scope = 'blog_ingest'

    @extend_schema(
        summary='블로그 글 자동 등록 (Ingest)',
        description=(
            '외부 프로젝트에서 작업 결과를 블로그 글로 등록한다. '
            '`X-Blog-Ingest-Key` 헤더의 전용 API 키로만 인증하며(JWT 미사용), '
            '`is_published`(기본값 `false`)로 즉시 공개 여부를 지정할 수 있다. '
            '`true`로 등록하면 `published_at`도 현재 시각으로 함께 설정된다. '
            '`category_name`은 기존에 존재하는 카테고리(대분류/소분류 무관) 이름과 정확히 일치해야 하며, '
            '없으면 422를 반환한다. 존재하는 카테고리 목록은 `GET /api/v1/blog/categories/`로 조회할 수 있다.'
        ),
        request=BlogIngestSerializer,
        responses={
            201: OpenApiResponse(description='글 생성 성공(초안 또는 공개)'),
            400: OpenApiResponse(description='입력 검증 오류'),
            403: OpenApiResponse(description='API 키 누락 또는 불일치'),
            422: OpenApiResponse(description='카테고리를 찾을 수 없음'),
        },
        tags=['blog'],
    )
    def post(self, request: Request) -> Response:
        serializer = BlogIngestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        try:
            category = get_category_by_name(data['category_name'])
        except CategoryNotFoundError:
            return Response(
                {'detail': f"카테고리 '{data['category_name']}'이 존재하지 않습니다. Admin에서 먼저 생성해주세요."},
                status=422,
            )
        post = Post.objects.create(
            title=data['title'],
            slug=generate_unique_slug(Post, data['title']),
            summary=data['summary'],
            content=data['content'],
            tags=data['tags'],
            category=category,
            repo_url=data['repo_url'],
            is_published=data['is_published'],
            published_at=timezone.now() if data['is_published'] else None,
        )

        return Response(
            {
                'id': post.id,
                'slug': post.slug,
                'admin_url': reverse('admin:blog_post_change', args=[post.id]),
            },
            status=201,
        )


class BlogCategoryListView(APIView):
    """ingest API에 사용할 수 있는 기존 카테고리 전체 목록을 조회하는 엔드포인트."""

    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = [HasBlogIngestKey]

    @extend_schema(
        summary='블로그 카테고리 목록 조회',
        description=(
            'ingest API(`POST /api/v1/blog/ingest/`)에서 사용할 수 있는 기존 카테고리 전체 목록을 반환한다. '
            '`X-Blog-Ingest-Key` 헤더의 전용 API 키로만 인증한다(JWT 미사용). '
            '`parent_name`이 `null`이면 대분류(최상위 카테고리)다.'
        ),
        responses={200: CategoryListSerializer(many=True)},
        tags=['blog'],
    )
    def get(self, request: Request) -> Response:
        categories = Category.objects.select_related('parent').all()
        serializer = CategoryListSerializer(categories, many=True)
        return Response(serializer.data)
