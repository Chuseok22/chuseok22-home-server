from apps.site.templatetags.profile_tags import skill_icon_url


def test_skill_icon_url은_슬러그를_simple_icons_cdn_url로_변환한다() -> None:
    assert skill_icon_url('django') == 'https://cdn.simpleicons.org/django'


def test_skill_icon_url은_완전한_url이면_그대로_반환한다() -> None:
    url = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.svg'

    assert skill_icon_url(url) == url
