from rest_framework import serializers

from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'category', 'title', 'description',
            'tags', 'status', 'order',
            'period', 'team_size', 'role', 'highlights',
            'github_href', 'demo_href', 'title_href',
        ]
