from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.blog.models import Post
from apps.blog.services.media_storage import delete_media_files, extract_media_paths


@receiver(post_delete, sender=Post)
def cleanup_post_media(sender: type[Post], instance: Post, **kwargs: object) -> None:
    # Admin의 대량 삭제(QuerySet.delete())에서도 개별 인스턴스 delete()와 달리
    # post_delete 시그널은 항상 발동하므로, Post.delete() 오버라이드 대신 시그널을 사용한다.
    delete_media_files(extract_media_paths(instance.content))
