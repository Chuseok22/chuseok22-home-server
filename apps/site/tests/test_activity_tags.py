from apps.site.templatetags.activity_tags import activity_icon, contribution_level_class


def test_activity_icon은_알려진_이벤트_타입을_이모지로_매핑한다() -> None:
    assert activity_icon('PushEvent') == '📝'
    assert activity_icon('PullRequestEvent') == '🔀'
    assert activity_icon('PullRequestReviewEvent') == '👀'
    assert activity_icon('CreateEvent') == '🎉'
    assert activity_icon('ReleaseEvent') == '🚀'
    assert activity_icon('IssuesEvent') == '🐛'


def test_activity_icon은_알수없는_타입에_기본_아이콘을_반환한다() -> None:
    assert activity_icon('WatchEvent') == '📌'


def test_contribution_level_class는_경계값별로_색상단계를_반환한다() -> None:
    assert contribution_level_class(0) == 'bg-base-300'
    assert contribution_level_class(1) == 'bg-success/30'
    assert contribution_level_class(3) == 'bg-success/30'
    assert contribution_level_class(4) == 'bg-success/55'
    assert contribution_level_class(6) == 'bg-success/55'
    assert contribution_level_class(7) == 'bg-success/80'
    assert contribution_level_class(9) == 'bg-success/80'
    assert contribution_level_class(10) == 'bg-success'
    assert contribution_level_class(100) == 'bg-success'
