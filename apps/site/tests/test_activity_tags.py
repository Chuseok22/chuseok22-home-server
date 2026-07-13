from apps.site.templatetags.activity_tags import activity_icon


def test_activity_icon은_알려진_이벤트_타입을_이모지로_매핑한다() -> None:
    assert activity_icon('PushEvent') == '📝'
    assert activity_icon('PullRequestEvent') == '🔀'
    assert activity_icon('PullRequestReviewEvent') == '👀'
    assert activity_icon('CreateEvent') == '🎉'
    assert activity_icon('ReleaseEvent') == '🚀'
    assert activity_icon('IssuesEvent') == '🐛'


def test_activity_icon은_알수없는_타입에_기본_아이콘을_반환한다() -> None:
    assert activity_icon('WatchEvent') == '📌'
