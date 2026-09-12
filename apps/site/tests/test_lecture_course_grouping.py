from apps.sejong.lecture.services.course import Course
from apps.site.services.lecture_course_grouping import CourseGroup, group_courses_by_semester


def _course(course_id: str, year: str, semester: str) -> Course:
    return Course(id=course_id, name=f'course-{course_id}', year=year, semester=semester)


def test_특정_연도_학기_지정시_그룹_헤더_없이_단일_그룹() -> None:
    courses = [_course('1', '2023', '10'), _course('2', '2023', '10')]

    groups = group_courses_by_semester(courses, year='2023', semester='10')

    assert groups == [CourseGroup(label=None, courses=courses)]


def test_연도가_전체일때_학기별로_그룹핑되고_최신연도가_먼저온다() -> None:
    courses = [
        _course('1', '2023', '10'),
        _course('2', '2026', '20'),
        _course('3', '2026', '10'),
    ]

    groups = group_courses_by_semester(courses, year='all', semester='10')

    assert [g.label for g in groups] == ['2026년 2학기', '2026년 1학기', '2023년 1학기']
    assert groups[0].courses == [courses[1]]
    assert groups[1].courses == [courses[2]]
    assert groups[2].courses == [courses[0]]


def test_학기가_전체일때_한_해_안에서_캘린더_역순으로_정렬된다() -> None:
    courses = [
        _course('1', '2026', '10'),
        _course('2', '2026', '21'),
        _course('3', '2026', '11'),
        _course('4', '2026', '20'),
    ]

    groups = group_courses_by_semester(courses, year='2026', semester='all')

    assert [g.label for g in groups] == [
        '2026년 겨울계절수업', '2026년 2학기', '2026년 여름계절수업', '2026년 1학기',
    ]


def test_그룹이_하나뿐이면_헤더_없이_평면_목록으로_반환() -> None:
    courses = [_course('1', '2026', '20'), _course('2', '2026', '20')]

    groups = group_courses_by_semester(courses, year='2026', semester='all')

    assert groups == [CourseGroup(label=None, courses=courses)]


def test_빈_강좌_목록은_빈_그룹_목록을_반환() -> None:
    assert group_courses_by_semester([], year='all', semester='all') == []


def test_알수없는_학기코드는_그해_안에서_맨_뒤로_정렬된다() -> None:
    """_parse_past_courses가 알 수 없는 라벨을 'all'로 폴백하므로, 그룹핑도 'all' 코드를
    깨지지 않고 처리해야 한다 - 표시는 어색해도(라벨 매핑에 없으므로 코드값 그대로 노출) 기능은
    유지된다."""
    courses = [
        _course('1', '2026', '10'),
        _course('2', '2026', 'all'),
    ]

    groups = group_courses_by_semester(courses, year='2026', semester='all')

    assert [g.label for g in groups] == ['2026년 1학기', '2026년 all']
