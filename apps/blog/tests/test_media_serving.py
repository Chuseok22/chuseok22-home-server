from django.test import Client


def test_media_url이_업로드된_파일을_서빙한다(client: Client, settings, tmp_path) -> None:
    settings.MEDIA_ROOT = tmp_path
    test_file = tmp_path / 'test_media_serving_sample.txt'
    test_file.write_text('hello')

    response = client.get('/media/test_media_serving_sample.txt')

    assert response.status_code == 200
    assert b''.join(response.streaming_content) == b'hello'
