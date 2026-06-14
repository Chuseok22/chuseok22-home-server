from rest_framework import serializers

from apps.activity.models import GithubActivity


class ActivityItemSerializer(serializers.ModelSerializer):
    """GitHub 활동 목록 응답 직렬화"""

    class Meta:
        model = GithubActivity
        fields = ('id', 'event_type', 'repo_name', 'title', 'meta', 'occurred_at')
