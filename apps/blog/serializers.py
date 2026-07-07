from rest_framework import serializers


class BlogIngestSerializer(serializers.Serializer):
    """블로그 ingest API 요청 검증. category_name은 소분류(저장소명)로 사용된다."""

    title = serializers.CharField(max_length=200)
    summary = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')
    content = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)
    category_name = serializers.CharField(max_length=50)
    repo_url = serializers.URLField(required=False, allow_blank=True, default='')
