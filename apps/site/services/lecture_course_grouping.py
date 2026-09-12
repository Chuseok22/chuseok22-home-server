from dataclasses import dataclass

from apps.sejong.lecture.services.course import Course, SEMESTER_LABEL_BY_CODE

_SEMESTER_CALENDAR_ORDER = {'10': 0, '11': 1, '20': 2, '21': 3}


@dataclass(frozen=True)
class CourseGroup:
    """강좌 조회 결과를 학기 단위로 묶은 그룹.

    label이 None이면 템플릿이 그룹 헤더(아코디언) 없이 강좌 목록만 렌더링해야 한다는 뜻이다 -
    특정 연도+특정 학기를 명시적으로 선택한 조회이거나, "전체" 조회 결과가 실제로는 학기 하나뿐인
    경우다.
    """

    label: str | None
    courses: list[Course]


def group_courses_by_semester(courses: list[Course], year: str, semester: str) -> list[CourseGroup]:
    """year 또는 semester가 'all'일 때만 실제로 (year, semester)별로 그룹핑한다.

    특정 연도+특정 학기를 명시적으로 선택한 조회는 애초에 한 학기 결과만 나오므로 그룹 헤더가
    필요 없다. 그룹은 연도 내림차순, 같은 연도 안에서는 캘린더 순서(1학기→여름계절수업→2학기→
    겨울계절수업)의 역순으로 정렬해 가장 최근 학기가 위로 오게 한다. `SEMESTER_LABEL_BY_CODE`에
    없는 코드(예: 알 수 없는 라벨을 'all'로 폴백한 경우)는 라벨 자리에 코드값을 그대로 노출하고
    정렬 우선순위는 그 연도 안에서 가장 뒤로 민다.
    """
    if not courses:
        return []
    if year != 'all' and semester != 'all':
        return [CourseGroup(label=None, courses=courses)]

    buckets: dict[tuple[str, str], list[Course]] = {}
    for course in courses:
        buckets.setdefault((course.year, course.semester), []).append(course)

    def sort_key(key: tuple[str, str]) -> tuple[int, int]:
        group_year, group_semester = key
        try:
            year_key = -int(group_year)
        except ValueError:
            year_key = 0
        return (year_key, -_SEMESTER_CALENDAR_ORDER.get(group_semester, -1))

    groups = [
        CourseGroup(
            label=f'{group_year}년 {SEMESTER_LABEL_BY_CODE.get(group_semester, group_semester)}',
            courses=group_courses,
        )
        for (group_year, group_semester), group_courses in sorted(
            buckets.items(), key=lambda item: sort_key(item[0]),
        )
    ]
    return groups if len(groups) > 1 else [CourseGroup(label=None, courses=courses)]
