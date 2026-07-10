from unittest.mock import Mock, patch

import requests

from apps.activity.services.github_stats import GithubStats, GithubStatsService


def _mock_response(json_data: dict, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = Mock()
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError('error')
    return response


def test_fetch는_GraphQL_응답을_GithubStats로_파싱한다(settings) -> None:
    settings.GITHUB_PAT = 'test-token'
    settings.GITHUB_USERNAME = 'testuser'

    payload = {
        'data': {
            'user': {
                'contributionsCollection': {
                    'contributionCalendar': {
                        'weeks': [
                            {
                                'contributionDays': [
                                    {'date': '2026-01-01', 'contributionCount': 3},
                                    {'date': '2026-01-02', 'contributionCount': 0},
                                ]
                            }
                        ]
                    }
                },
                'repositories': {
                    'nodes': [
                        {'stargazerCount': 2},
                        {'stargazerCount': 1},
                    ]
                },
            }
        }
    }

    with patch(
        'apps.activity.services.github_stats.requests.post',
        return_value=_mock_response(payload),
    ) as mock_post:
        result = GithubStatsService().fetch()

    assert mock_post.called
    assert result.total_stars == 3
    assert len(result.contribution_days) == 2
    assert result.contribution_days[0].date.isoformat() == '2026-01-01'
    assert result.contribution_days[0].contribution_count == 3


def test_fetch는_GITHUB_PAT_미설정시_빈_결과를_반환한다(settings) -> None:
    settings.GITHUB_PAT = ''
    settings.GITHUB_USERNAME = 'testuser'

    result = GithubStatsService().fetch()

    assert result == GithubStats(contribution_days=(), total_stars=0)


def test_fetch는_네트워크_오류시_빈_결과를_반환한다(settings) -> None:
    settings.GITHUB_PAT = 'test-token'
    settings.GITHUB_USERNAME = 'testuser'

    with patch(
        'apps.activity.services.github_stats.requests.post',
        side_effect=requests.ConnectionError('연결 실패'),
    ):
        result = GithubStatsService().fetch()

    assert result == GithubStats(contribution_days=(), total_stars=0)


def test_fetch는_GraphQL_errors_필드가_있으면_빈_결과를_반환한다(settings) -> None:
    settings.GITHUB_PAT = 'test-token'
    settings.GITHUB_USERNAME = 'testuser'

    payload = {'errors': [{'message': 'Could not resolve to a User'}]}

    with patch(
        'apps.activity.services.github_stats.requests.post',
        return_value=_mock_response(payload),
    ):
        result = GithubStatsService().fetch()

    assert result == GithubStats(contribution_days=(), total_stars=0)


def test_fetch는_컨트리뷰션_day에_필수_키가_없으면_해당_day를_건너뛴다(settings) -> None:
    settings.GITHUB_PAT = 'test-token'
    settings.GITHUB_USERNAME = 'testuser'

    payload = {
        'data': {
            'user': {
                'contributionsCollection': {
                    'contributionCalendar': {
                        'weeks': [
                            {
                                'contributionDays': [
                                    {'date': '2026-01-01', 'contributionCount': 3},
                                    {'date': '2026-01-02'},
                                ]
                            }
                        ]
                    }
                },
                'repositories': {'nodes': []},
            }
        }
    }

    with patch(
        'apps.activity.services.github_stats.requests.post',
        return_value=_mock_response(payload),
    ):
        result = GithubStatsService().fetch()

    assert len(result.contribution_days) == 1
    assert result.contribution_days[0].date.isoformat() == '2026-01-01'
    assert result.contribution_days[0].contribution_count == 3
