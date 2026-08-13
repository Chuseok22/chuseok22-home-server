import calendar
from dataclasses import dataclass, field
from datetime import date

from django.db.models import Q

from apps.certifications.models import CertificationDefinition, ExamSchedule

_LABELS = {
    'registration_start': '접수시작',
    'registration_end': '접수마감',
    'exam_date': '시험일',
    'result_announcement_date': '발표일',
}


@dataclass(frozen=True)
class CalendarDay:
    day_date: date
    is_current_month: bool
    schedules: list[dict] = field(default_factory=list)


def build_month_calendar(year: int, month: int, category: str | None = None) -> list[list[CalendarDay]]:
    """해당 월의 캘린더 그리드(주 단위 리스트, 일요일 시작)를 만든다.
    이전/다음 달로 걸치는 날짜도 채우되 is_current_month=False로 표시한다."""
    weeks_of_dates = calendar.Calendar(firstweekday=6).monthdatescalendar(year, month)
    badges_by_date = _badges_by_date(weeks_of_dates[0][0], weeks_of_dates[-1][-1], category)
    return [
        [
            CalendarDay(
                day_date=day, is_current_month=(day.month == month),
                schedules=badges_by_date.get(day, []),
            )
            for day in week
        ]
        for week in weeks_of_dates
    ]


def _badges_by_date(range_start: date, range_end: date, category: str | None) -> dict[date, list[dict]]:
    queryset = ExamSchedule.objects.filter(certification__is_active=True).select_related('certification')
    if category:
        queryset = queryset.filter(certification__category=category)
    queryset = queryset.filter(
        Q(registration_start__range=(range_start, range_end))
        | Q(registration_end__range=(range_start, range_end))
        | Q(exam_date__range=(range_start, range_end))
        | Q(result_announcement_date__range=(range_start, range_end)),
    )

    result: dict[date, list[dict]] = {}
    for schedule in queryset:
        for field_name, label in _LABELS.items():
            day = getattr(schedule, field_name)
            if day is None or not (range_start <= day <= range_end):
                continue
            result.setdefault(day, []).append({
                'label': label,
                'certification_name': schedule.certification.name,
                'round_name': schedule.round_name,
            })
    return result


def get_upcoming_schedules(today: date, category: str | None = None, limit: int = 20) -> list[ExamSchedule]:
    """오늘 이후 접수마감일 기준으로 다가오는 일정을 오름차순으로 반환한다(타임라인 뷰용)."""
    queryset = ExamSchedule.objects.filter(
        certification__is_active=True, registration_end__gte=today,
    ).select_related('certification')
    if category:
        queryset = queryset.filter(certification__category=category)
    return list(queryset.order_by('registration_end')[:limit])


def get_tracked_certifications(category: str | None = None) -> list[CertificationDefinition]:
    """추적 중(is_active=True)인 전체 자격증 목록을 반환한다.
    is_always_open=True인 자격증(예: CCNA)은 ExamSchedule이 없어 캘린더/타임라인에 나타나지
    않으므로, '추적 중인 자격증' 목록에서만 노출한다."""
    queryset = CertificationDefinition.objects.filter(is_active=True)
    if category:
        queryset = queryset.filter(category=category)
    return list(queryset)
