import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.test import RequestFactory

from apps.accounts.signals import promote_owner_if_matched

User = get_user_model()


@pytest.mark.django_db
def test_GITHUB_OWNER_ID와_uid가_일치하면_is_staff_승격(settings) -> None:
    from allauth.socialaccount.models import SocialAccount

    settings.GITHUB_OWNER_ID = '12345'
    user = User.objects.create_user(username='chuseok22-gh', is_staff=False)
    SocialAccount.objects.create(
        user=user, provider='github', uid='12345',
        extra_data={'login': 'Chuseok22'},
    )

    request = RequestFactory().get('/')
    user_logged_in.send(sender=User, request=request, user=user)

    user.refresh_from_db()
    assert user.is_staff is True


@pytest.mark.django_db
def test_다른_GITHUB_계정은_승격되지_않는다(settings) -> None:
    from allauth.socialaccount.models import SocialAccount

    settings.GITHUB_OWNER_ID = '12345'
    user = User.objects.create_user(username='other-gh', is_staff=False)
    SocialAccount.objects.create(
        user=user, provider='github', uid='99999',
        extra_data={'login': 'someone-else'},
    )

    request = RequestFactory().get('/')
    user_logged_in.send(sender=User, request=request, user=user)

    user.refresh_from_db()
    assert user.is_staff is False
