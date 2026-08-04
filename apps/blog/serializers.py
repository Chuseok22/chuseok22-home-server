from rest_framework import serializers

from apps.blog.models import Category


class BlogIngestSerializer(serializers.Serializer):
    """블로그 ingest API 요청 검증. category_name은 기존 카테고리(대분류/소분류 무관) 이름과 정확히 일치해야 한다."""

    title = serializers.CharField(max_length=200)
    summary = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')
    content = serializers.CharField(max_length=50000)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)
    category_name = serializers.CharField(max_length=50)
    repo_url = serializers.URLField(required=False, allow_blank=True, default='')
    is_published = serializers.BooleanField(required=False, default=False)


class CategoryListSerializer(serializers.Serializer):
    """카테고리 목록 조회 API 응답 직렬화."""

    name = serializers.CharField()
    slug = serializers.CharField()
    parent_name = serializers.SerializerMethodField()

    def get_parent_name(self, obj: Category) -> str | None:
        return obj.parent.name if obj.parent else None


class BlogIngestImageUploadSerializer(serializers.Serializer):
    """블로그 ingest용 이미지/파일 업로드 요청 검증. 파일 1~10개."""

    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=10,
    )


class BlogIngestImageUploadResultSerializer(serializers.Serializer):
    """이미지/파일 업로드 결과 응답 아이템. 파일 단위로 성공/실패를 구분한다."""

    filename = serializers.CharField()
    success = serializers.BooleanField()
    url = serializers.CharField(allow_blank=True)
    markdown = serializers.CharField(allow_blank=True)
    error_message = serializers.CharField(allow_blank=True)


class BlogIngestImageUploadResponseSerializer(serializers.Serializer):
    """이미지/파일 업로드 API의 응답 스키마 문서화용. 실제 응답 본문({"results": [...]})과 구조를 맞추기 위해 존재하며 런타임에는 인스턴스화하지 않는다."""

    results = BlogIngestImageUploadResultSerializer(many=True)
