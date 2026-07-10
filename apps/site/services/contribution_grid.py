from collections.abc import Iterable

from apps.activity.models import GithubContributionDay


def build_contribution_weeks(days: Iterable[GithubContributionDay]) -> list[list[GithubContributionDay]]:
    """날짜순으로 정렬된 컨트리뷰션 목록을 7일 단위 주(week) 리스트로 그룹핑한다.

    실제 요일에 맞춘 캘린더 정렬은 하지 않고 순서대로 7개씩 잘라 묶는
    단순한 방식이다 — 홈 화면 위젯 용도로는 이 정도 단순화로 충분하다.
    """
    day_list = list(days)
    return [day_list[i:i + 7] for i in range(0, len(day_list), 7)]
