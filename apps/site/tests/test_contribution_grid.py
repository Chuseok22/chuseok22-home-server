from datetime import date

from apps.activity.models import GithubContributionDay
from apps.site.services.contribution_grid import build_contribution_weeks


def test_build_contribution_weeks는_7일_단위로_묶는다() -> None:
    days = [
        GithubContributionDay(date=date(2026, 1, i), contribution_count=i)
        for i in range(1, 8)
    ]

    weeks = build_contribution_weeks(days)

    assert len(weeks) == 1
    assert len(weeks[0]) == 7
    assert weeks[0][0].contribution_count == 1


def test_build_contribution_weeks는_7의_배수가_아니면_마지막_주가_짧다() -> None:
    days = [
        GithubContributionDay(date=date(2026, 1, i), contribution_count=i)
        for i in range(1, 10)
    ]

    weeks = build_contribution_weeks(days)

    assert len(weeks) == 2
    assert len(weeks[0]) == 7
    assert len(weeks[1]) == 2


def test_build_contribution_weeks는_빈_입력이면_빈_리스트를_반환한다() -> None:
    assert build_contribution_weeks([]) == []
