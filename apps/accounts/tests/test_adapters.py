from allauth.socialaccount.models import SocialLogin
from django.test import RequestFactory

from apps.accounts.adapters import AllowSocialSignupAdapter, NoLocalSignupAccountAdapter


def test_이메일_비밀번호_자체_회원가입은_차단된다() -> None:
    adapter = NoLocalSignupAccountAdapter()
    request = RequestFactory().get('/')

    assert adapter.is_open_for_signup(request) is False


def test_GitHub_소셜_로그인_신규_가입은_허용된다() -> None:
    adapter = AllowSocialSignupAdapter()
    request = RequestFactory().get('/')
    sociallogin = SocialLogin()

    assert adapter.is_open_for_signup(request, sociallogin=sociallogin) is True
