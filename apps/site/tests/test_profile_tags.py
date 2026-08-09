from apps.site.templatetags.profile_tags import activity_link_icon, skill_icon_url


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
