from apps.sejong.library.services.study_room import RoomSlot, StudyRoom
from apps.site.services.library_matrix import build_room_matrix


def _room(name: str, seat_cnt: int, slots: tuple[RoomSlot, ...]) -> StudyRoom:
    return StudyRoom(
        room_name=name, group_title='그룹', seat_cnt=seat_cnt,
        room_gb='S1', sroom_title='그룹스터디룸6인실', seq='0', slots=slots,
    )


def test_시간_컬럼은_전체_룸의_시간_합집합을_정렬해서_반환한다() -> None:
    room_a = _room('01스터디룸', 6, (
        RoomSlot(time_label='09:00', is_available=True),
        RoomSlot(time_label='11:00', is_available=False),
    ))
    room_b = _room('02스터디룸', 6, (
        RoomSlot(time_label='10:00', is_available=True),
    ))

    matrix = build_room_matrix([room_a, room_b])

    assert matrix.time_labels == ('09:00', '10:00', '11:00')


def test_룸에_없는_시간대의_셀은_slot이_None이다() -> None:
    room_a = _room('01스터디룸', 6, (RoomSlot(time_label='09:00', is_available=True),))
    room_b = _room('02스터디룸', 6, (RoomSlot(time_label='10:00', is_available=True),))

    matrix = build_room_matrix([room_a, room_b])
    row_a = next(r for r in matrix.rows if r.room_name == '01스터디룸')

    cell_0900 = next(c for c in row_a.cells if c.time_label == '09:00')
    cell_1000 = next(c for c in row_a.cells if c.time_label == '10:00')
    assert cell_0900.slot is not None
    assert cell_1000.slot is None


def test_각_행의_셀_개수는_전체_시간_컬럼_수와_같다() -> None:
    room_a = _room('01스터디룸', 6, (RoomSlot(time_label='09:00', is_available=True),))
    room_b = _room('02스터디룸', 6, (
        RoomSlot(time_label='09:00', is_available=True),
        RoomSlot(time_label='10:00', is_available=True),
    ))

    matrix = build_room_matrix([room_a, room_b])

    assert all(len(row.cells) == len(matrix.time_labels) for row in matrix.rows)


def test_빈_룸_목록이면_빈_매트릭스를_반환한다() -> None:
    matrix = build_room_matrix([])

    assert matrix.time_labels == ()
    assert matrix.rows == ()


def test_행_순서는_입력된_룸_순서를_유지한다() -> None:
    room_a = _room('02스터디룸', 6, (RoomSlot(time_label='09:00', is_available=True),))
    room_b = _room('01스터디룸', 12, (RoomSlot(time_label='09:00', is_available=True),))

    matrix = build_room_matrix([room_a, room_b])

    assert [r.room_name for r in matrix.rows] == ['02스터디룸', '01스터디룸']
