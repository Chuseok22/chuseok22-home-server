import pytest

from apps.sejong.library.services.validation import validate_attendee_count


@pytest.mark.parametrize(
    'seat_cnt,attendee_count,expected',
    [
        (6, 3, None),   # 정확히 절반
        (6, 6, None),   # 최대
        (6, 4, None),   # 절반 초과, 정원 이하
        (4, 2, None),   # 정원 4명, 절반(ceil(4/2)=2)
    ],
)
def test_validate_attendee_count_passes_within_range(seat_cnt, attendee_count, expected) -> None:
    assert validate_attendee_count(seat_cnt, attendee_count) is expected


def test_validate_attendee_count_fails_below_half() -> None:
    message = validate_attendee_count(6, 2)
    assert message == '정원(6명)의 절반 이상인 최소 3명, 최대 6명이 필요합니다.'


def test_validate_attendee_count_fails_above_capacity() -> None:
    message = validate_attendee_count(6, 7)
    assert message == '정원(6명)의 절반 이상인 최소 3명, 최대 6명이 필요합니다.'


def test_validate_attendee_count_odd_capacity_rounds_up_minimum() -> None:
    # seat_cnt=5 → ceil(5/2)=3이 최소 인원
    assert validate_attendee_count(5, 2) is not None
    assert validate_attendee_count(5, 3) is None
