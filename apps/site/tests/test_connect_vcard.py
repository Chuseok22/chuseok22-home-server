from apps.site.models import ConnectProfile
from apps.site.services.vcard import build_vcard

_WEBSITE_URL = 'https://chuseok22.com/'


def _build_profile(**overrides: str) -> ConnectProfile:
    values = {
        'english_name': 'Jihoon Baek',
        'title': 'Computer Science and Engineering\nUndergraduate Student',
        'email': 'me@example.com',
        'phone': '+82-10-0000-0000',
    }
    values.update(overrides)
    return ConnectProfile(**values)


def test_build_vcard는_전체_필드를_vcard_3_0_형식으로_출력한다() -> None:
    vcard = build_vcard(_build_profile(), _WEBSITE_URL)

    assert vcard == (
        'BEGIN:VCARD\r\n'
        'VERSION:3.0\r\n'
        'N:Baek;Jihoon;;;\r\n'
        'FN:Jihoon Baek\r\n'
        'TITLE:Computer Science and Engineering\\, Undergraduate Student\r\n'
        'TEL;TYPE=CELL:+82-10-0000-0000\r\n'
        'EMAIL;TYPE=INTERNET:me@example.com\r\n'
        'URL:https://chuseok22.com/\r\n'
        'END:VCARD\r\n'
    )


def test_build_vcard는_admin_textarea의_crlf_직함을_정리한다() -> None:
    vcard = build_vcard(_build_profile(title='A\r\nB'), _WEBSITE_URL)

    assert 'TITLE:A\\, B' in vcard
    assert '\r' not in vcard.replace('\r\n', '')
    assert '\n' not in vcard.replace('\r\n', '')


def test_build_vcard는_이름에_섞인_줄바꿈으로_속성을_주입할_수_없다() -> None:
    vcard = build_vcard(_build_profile(english_name='X\r\nTEL:1'), _WEBSITE_URL)

    assert not any(line.startswith('TEL:1') for line in vcard.split('\r\n'))


def test_build_vcard는_전화번호와_이메일이_비면_해당_줄을_생략한다() -> None:
    vcard = build_vcard(_build_profile(phone='', email=''), _WEBSITE_URL)

    assert 'TEL' not in vcard
    assert 'EMAIL' not in vcard


def test_build_vcard는_한_단어_이름을_성으로_처리한다() -> None:
    vcard = build_vcard(_build_profile(english_name='Jihoon'), _WEBSITE_URL)

    assert 'N:Jihoon;;;;' in vcard
    assert 'FN:Jihoon' in vcard


def test_build_vcard는_공백뿐인_이름이면_빈_n_속성을_출력한다() -> None:
    vcard = build_vcard(_build_profile(english_name='   '), _WEBSITE_URL)

    assert 'N:;;;;\r\n' in vcard
    assert 'FN:   \r\n' in vcard


def test_build_vcard는_직함이_비면_title_줄을_생략한다() -> None:
    vcard = build_vcard(_build_profile(title='\r\n  \n'), _WEBSITE_URL)

    assert 'TITLE' not in vcard


def test_build_vcard는_특수문자를_이스케이프한다() -> None:
    vcard = build_vcard(_build_profile(title='A;B,C\\D'), _WEBSITE_URL)

    assert 'TITLE:A\\;B\\,C\\\\D' in vcard
