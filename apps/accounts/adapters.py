from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpRequest


class NoLocalSignupAccountAdapter(DefaultAccountAdapter):
    """이메일/비밀번호 기반 자체 회원가입을 막고 GitHub 소셜 로그인만 허용한다."""

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return False
