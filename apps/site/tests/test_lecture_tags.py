from apps.sejong.lecture.services.course import Course
from apps.site.templatetags.lecture_tags import contains_course_id


def _course(course_id: str) -> Course:
    return Course(id=course_id, name=f'course-{course_id}', year='2026', semester='20')


def test_course_id가_목록에_있으면_True() -> None:
    courses = [_course('1'), _course('2')]

    assert contains_course_id(courses, '2') is True


def test_course_id가_목록에_없으면_False() -> None:
    courses = [_course('1'), _course('2')]

    assert contains_course_id(courses, '999') is False


def test_course_id가_None이면_False() -> None:
    courses = [_course('1')]

    assert contains_course_id(courses, None) is False


def test_빈_목록이면_False() -> None:
    assert contains_course_id([], '1') is False
