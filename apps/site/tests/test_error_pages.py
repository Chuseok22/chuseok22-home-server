import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
@override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
def test_존재하지_않는_페이지는_커스텀_404() -> None:
    client = Client(raise_request_exception=False)
    response = client.get('/no-such-page/')

    assert response.status_code == 404
    assert '페이지를 찾을 수 없습니다' in response.content.decode()
