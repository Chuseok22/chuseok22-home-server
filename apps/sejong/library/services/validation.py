import math


def validate_attendee_count(seat_cnt: int, attendee_count: int) -> str | None:
    """정원의 절반 이상 ~ 정원 이하가 아니면 에러 메시지를, 조건을 만족하면 None을 반환한다."""
    min_required = math.ceil(seat_cnt / 2)
    if not (min_required <= attendee_count <= seat_cnt):
        return f'정원({seat_cnt}명)의 절반 이상인 최소 {min_required}명, 최대 {seat_cnt}명이 필요합니다.'
    return None
