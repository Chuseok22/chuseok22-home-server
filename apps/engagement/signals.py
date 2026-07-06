import logging
from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.engagement.models import Comment, Like
from apps.notifications.services.telegram import TelegramService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Comment)
def notify_admin_on_comment(sender: type[Comment], instance: Comment, created: bool, **kwargs: Any) -> None:
    if not created:
        return
    message = f'💬 새 댓글\n{instance.author}: {instance.body}\n대상: {instance.target}'
    TelegramService().send_admin_alert(message)


@receiver(post_save, sender=Like)
def notify_admin_on_like(sender: type[Like], instance: Like, created: bool, **kwargs: Any) -> None:
    if not created:
        return
    message = f'❤️ 새 좋아요\n{instance.user} → {instance.target}'
    TelegramService().send_admin_alert(message)
