from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from django.http import HttpRequest


class NoLocalSignupAccountAdapter(DefaultAccountAdapter):
    """이메일/비밀번호 기반 자체 회원가입을 막고 GitHub 소셜 로그인만 허용한다."""

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return False


class AllowSocialSignupAdapter(DefaultSocialAccountAdapter):
    """소셜 로그인(현재는 GitHub만 등록됨) 신규 가입을 허용한다.

    DefaultSocialAccountAdapter.is_open_for_signup()은 기본적으로
    ACCOUNT_ADAPTER(NoLocalSignupAccountAdapter)의 is_open_for_signup()을 그대로
    위임 호출하므로, 별도로 재정의하지 않으면 소셜 신규 가입까지 함께 차단된다.
    """

    def is_open_for_signup(self, request: HttpRequest, sociallogin: SocialLogin) -> bool:
        return True
