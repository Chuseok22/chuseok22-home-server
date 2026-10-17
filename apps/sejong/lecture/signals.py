from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.sejong.lecture.models import SejongAccount
from apps.sejong.lecture.services.ecampus_auth import EcampusMoodleAuthService


@receiver(post_save, sender=SejongAccount)
@receiver(post_delete, sender=SejongAccount)
def evict_account_session(sender: type[SejongAccount], instance: SejongAccount, **kwargs: Any) -> None:
    EcampusMoodleAuthService.evict_account(instance.pk)
