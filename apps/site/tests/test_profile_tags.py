from datetime import date, timedelta

from apps.profile.services.visitor_counter import DailyCount
from apps.site.templatetags.profile_tags import activity_link_icon, skill_icon_url, visitor_sparkline


def test_skill_icon_url은_슬러그를_simple_icons_cdn_url로_변환한다() -> None:
    assert skill_icon_url('django') == 'https://cdn.simpleicons.org/django'


def test_skill_icon_url은_완전한_url이면_그대로_반환한다() -> None:
    url = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.svg'

    assert skill_icon_url(url) == url


def test_activity_link_icon은_github_타입을_simple_icons_url로_변환한다() -> None:
    result = activity_link_icon('github')

    assert result == {'label': 'GitHub', 'icon_url': 'https://cdn.simpleicons.org/github'}


def test_activity_link_icon은_official_타입을_heroicons_url_그대로_반환한다() -> None:
    result = activity_link_icon('official')

    assert result == {
        'label': '공식 페이지',
        'icon_url': 'https://cdn.jsdelivr.net/npm/heroicons@2/24/outline/globe-alt.svg',
    }


def test_activity_link_icon은_정의되지_않은_타입이면_other로_대체한다() -> None:
    result = activity_link_icon('알수없는타입')

    assert result['label'] == '링크'
    assert result['icon_url'] == 'https://cdn.jsdelivr.net/npm/heroicons@2/24/outline/link.svg'


def _recent_visits(counts: list[int]) -> list[DailyCount]:
    first_day = date(2026, 9, 25)
    return [DailyCount(date=first_day + timedelta(days=offset), count=count) for offset, count in enumerate(counts)]


def test_visitor_sparkline은_최댓값을_위쪽에_맞춘_선과_면_좌표를_만든다() -> None:
    context = visitor_sparkline(_recent_visits([0, 0, 0, 0, 0, 0, 10]))

    assert context['line_points'] == '0,56 43,56 85,56 128,56 171,56 213,56 256,8'
    assert context['area_points'] == '0,56 0,56 43,56 85,56 128,56 171,56 213,56 256,8 256,56'
    assert (context['dot_x'], context['dot_y']) == (256, 8)


def test_visitor_sparkline은_모두_0이면_바닥선으로_그린다() -> None:
    context = visitor_sparkline(_recent_visits([0, 0, 0, 0, 0, 0, 0]))

    assert context['line_points'] == '0,56 43,56 85,56 128,56 171,56 213,56 256,56'
    assert (context['dot_x'], context['dot_y']) == (256, 56)


def test_visitor_sparkline은_중간값을_최댓값_비율로_배치한다() -> None:
    context = visitor_sparkline(_recent_visits([5, 0, 0, 0, 0, 0, 10]))

    assert context['line_points'].startswith('0,32 ')


def test_visitor_sparkline_label은_날짜별_값과_오늘을_담는다() -> None:
    context = visitor_sparkline(_recent_visits([4, 7, 3, 9, 5, 6, 12]))

    assert context['label'] == '최근 7일 방문자: 9/25 4, 9/26 7, 9/27 3, 9/28 9, 9/29 5, 9/30 6, 오늘 12'


def test_visitor_sparkline은_하루치만_있어도_예외없이_왼쪽에_점을_둔다() -> None:
    context = visitor_sparkline(_recent_visits([5]))

    assert context['line_points'] == '0,8'
    assert (context['dot_x'], context['dot_y']) == (0, 8)
