from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class _Slot(Protocol):
    time_label: str
    is_available: bool
    room_no: str | None
    room_gb: str | None
    sroom_title: str | None
    room_name: str | None
    seq: str | None
    start_time: str | None


class _Room(Protocol):
    room_name: str
    seat_cnt: int
    slots: tuple[_Slot, ...]


@dataclass(frozen=True)
class MatrixCell:
    time_label: str
    slot: _Slot | None


@dataclass(frozen=True)
class MatrixRow:
    room_name: str
    seat_cnt: int
    cells: tuple[MatrixCell, ...]


@dataclass(frozen=True)
class RoomMatrix:
    time_labels: tuple[str, ...]
    rows: tuple[MatrixRow, ...]


def build_room_matrix(rooms: Sequence[_Room]) -> RoomMatrix:
    """룸 목록을 룸×시간 매트릭스로 변환한다.

    시간 컬럼은 전체 룸의 time_label 합집합을 정렬한 값이다 — 룸(그룹)마다 운영 시간이
    다를 수 있어 특정 룸에 없는 시간대는 MatrixCell.slot이 None이 된다.
    """
    time_labels = tuple(sorted({slot.time_label for room in rooms for slot in room.slots}))
    rows = tuple(_build_row(room, time_labels) for room in rooms)
    return RoomMatrix(time_labels=time_labels, rows=rows)


def _build_row(room: _Room, time_labels: tuple[str, ...]) -> MatrixRow:
    slot_by_time = _slot_by_time(room.slots)
    return MatrixRow(
        room_name=room.room_name,
        seat_cnt=room.seat_cnt,
        cells=tuple(
            MatrixCell(time_label=t, slot=slot_by_time.get(t))
            for t in time_labels
        ),
    )


def _slot_by_time(slots: tuple[_Slot, ...]) -> dict[str, _Slot]:
    return {slot.time_label: slot for slot in slots}
