import pytest


@pytest.mark.django_db
def test_pytest_django_설정_로드_확인() -> None:
    """pytest-django가 Django 설정을 정상적으로 로드하는지 확인한다."""
    from django.conf import settings

    assert settings.configured is True
