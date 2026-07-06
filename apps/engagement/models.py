from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Comment(models.Model):
    """임의의 모델(Post, Project, Tool 등)에 붙는 범용 댓글."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engagement_comment'
        ordering = ['created_at']
        indexes = [models.Index(fields=['content_type', 'object_id'])]

    def __str__(self) -> str:
        return f'{self.author}: {self.body[:20]}'


class Like(models.Model):
    """임의의 모델에 붙는 범용 좋아요. 사용자당 대상별 1개만 허용."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'object_id')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'engagement_like'
        indexes = [models.Index(fields=['content_type', 'object_id'])]
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'user'],
                name='unique_like_per_user_per_target',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user} likes {self.target}'
