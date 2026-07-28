from apps.notifications.models import NoticeSource


def test_icon_기본값은_빈_문자열이다() -> None:
    source = NoticeSource(name='테스트 소스', url='https://example.com', crawler_type='sejong')

    assert source.icon == ''
