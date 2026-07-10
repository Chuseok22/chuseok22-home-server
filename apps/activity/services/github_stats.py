import logging
from dataclasses import dataclass
from datetime import date, datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_GRAPHQL_URL = 'https://api.github.com/graphql'
_REQUEST_TIMEOUT = 10

_QUERY = '''
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        stargazerCount
      }
    }
  }
}
'''


@dataclass(frozen=True)
class ContributionDay:
    """컨트리뷰션 캘린더의 하루치 데이터"""
    date: date
    contribution_count: int


@dataclass(frozen=True)
class GithubStats:
    """GraphQL로 조회한 컨트리뷰션 캘린더 + 총 star 수"""
    contribution_days: tuple[ContributionDay, ...]
    total_stars: int


class GithubStatsService:
    """GitHub GraphQL API로 컨트리뷰션 캘린더·총 star 수를 조회한다.

    소유(fork 제외) 저장소를 최대 100개까지 집계한다(GraphQL first: 100 상한).
    현재 저장소 수로는 충분하며, 100개를 초과하면 페이지네이션이 필요하다.
    """

    def __init__(self) -> None:
        self.username: str = settings.GITHUB_USERNAME
        self.token: str = settings.GITHUB_PAT
        if not self.token:
            logger.warning('GITHUB_PAT가 설정되지 않아 GitHub 통계 수집이 비활성화됩니다.')

    def fetch(self) -> GithubStats:
        """실패 시 예외 전파 없이 빈 GithubStats를 반환한다."""
        if not self.token:
            return GithubStats(contribution_days=(), total_stars=0)

        user = self._request()
        if user is None:
            return GithubStats(contribution_days=(), total_stars=0)

        return self._parse(user)

    def _request(self) -> dict | None:
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json',
        }
        try:
            response = requests.post(
                _GRAPHQL_URL,
                json={'query': _QUERY, 'variables': {'login': self.username}},
                headers=headers,
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as e:
            logger.error('GitHub GraphQL 요청 실패: %s', e)
            return None
        except ValueError as e:  # JSON 파싱 실패
            logger.error('GitHub GraphQL 응답 파싱 실패: %s', e)
            return None

        if 'errors' in payload:
            logger.error('GitHub GraphQL 응답에 오류가 포함됨: %s', payload['errors'])
            return None

        user = payload.get('data', {}).get('user')
        if user is None:
            logger.error('GitHub GraphQL 응답에 user 데이터가 없음')
            return None
        return user

    def _parse(self, user: dict) -> GithubStats:
        weeks = user.get('contributionsCollection', {}).get('contributionCalendar', {}).get('weeks', [])
        contribution_days = tuple(
            ContributionDay(
                date=datetime.strptime(day['date'], '%Y-%m-%d').date(),
                contribution_count=day['contributionCount'],
            )
            for week in weeks
            for day in week.get('contributionDays', [])
        )

        repo_nodes = user.get('repositories', {}).get('nodes', [])
        total_stars = sum(node.get('stargazerCount', 0) for node in repo_nodes)

        return GithubStats(contribution_days=contribution_days, total_stars=total_stars)
