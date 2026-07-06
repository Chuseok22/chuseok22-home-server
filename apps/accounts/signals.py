import logging
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.http import HttpRequest

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def promote_owner_if_matched(sender: type[User], request: HttpRequest, user: User, **kwargs: Any) -> None:
    """로그인한 GitHub 계정(uid)이 사이트 소유자와 일치하면 is_staff로 승격한다."""
    from allauth.socialaccount.models import SocialAccount

    owner_id = settings.GITHUB_OWNER_ID
    if not owner_id or user.is_staff:
        return

    social_account = SocialAccount.objects.filter(user=user, provider='github').first()
    if social_account is None:
        return

    if social_account.uid == owner_id:
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        logger.info('소유자 GitHub 계정(uid=%s) 로그인 — is_staff 승격', social_account.uid)
