from django.conf import settings
from django.test import Client


def test_media_url이_업로드된_파일을_서빙한다(client: Client) -> None:
    media_root = settings.MEDIA_ROOT
    media_root.mkdir(parents=True, exist_ok=True)
    test_file = media_root / 'test_media_serving_sample.txt'
    test_file.write_text('hello')

    try:
        response = client.get('/media/test_media_serving_sample.txt')
        assert response.status_code == 200
        assert b''.join(response.streaming_content) == b'hello'
    finally:
        test_file.unlink()
