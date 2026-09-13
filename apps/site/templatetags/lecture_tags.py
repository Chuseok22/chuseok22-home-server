from django import template

from apps.sejong.lecture.services.course import Course

register = template.Library()


@register.filter
def contains_course_id(courses: list[Course], course_id: str | None) -> bool:
    """course_id가 courses 목록 안의 어느 강좌와도 일치하면 True.

    학기 아코디언 그룹의 체크박스를 열어둘지 판정하는 데 쓰인다 - 인라인으로 펼쳐진 강좌를
    포함하는 그룹은 이미 열려 있어야 사용자가 방금 클릭한 강좌를 계속 볼 수 있다. 학기 그룹
    체크박스는 서로 독립적(라디오 아님)이라 여러 그룹이 동시에 열려도 문제없다.
    """
    if not course_id:
        return False
    return any(course.id == course_id for course in courses)
