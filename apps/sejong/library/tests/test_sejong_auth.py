from types import SimpleNamespace

from apps.sejong.library.services.sejong_auth import _extract_token_from_chain


def test_extract_token_from_chain_preserves_plus_character() -> None:
    response = SimpleNamespace(
        url=(
            'https://libseat.sejong.ac.kr/mobile/MA/seatMain.php'
            '?token=+aKUmmZWL3BNdNihPzVcfOS/7t5qtqNF3trT647vDKo%3D'
        ),
        history=[],
    )

    assert _extract_token_from_chain(response) == '+aKUmmZWL3BNdNihPzVcfOS/7t5qtqNF3trT647vDKo='


def test_extract_token_from_chain_returns_none_when_host_not_libseat() -> None:
    response = SimpleNamespace(
        url='https://portal.sejong.ac.kr/some/path?token=abc123',
        history=[],
    )

    assert _extract_token_from_chain(response) is None


def test_extract_token_from_chain_falls_back_to_history() -> None:
    response = SimpleNamespace(
        url='https://libseat.sejong.ac.kr/mobile/MA/seatMain.php',
        history=[
            SimpleNamespace(url='https://libseat.sejong.ac.kr/mobile/MA/seatMain.php?token=abc123'),
        ],
    )

    assert _extract_token_from_chain(response) == 'abc123'


def test_extract_token_from_chain_returns_none_when_no_token_param() -> None:
    response = SimpleNamespace(
        url='https://libseat.sejong.ac.kr/mobile/MA/seatMain.php',
        history=[],
    )

    assert _extract_token_from_chain(response) is None
