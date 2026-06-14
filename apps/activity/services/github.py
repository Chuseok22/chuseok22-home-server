import logging
from dataclasses import dataclass
from datetime import datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_API_BASE = 'https://api.github.com'
_REQUEST_TIMEOUT = 10
_MAX_PAGES = 3          # page 1~3 (최대 300개)
_PER_PAGE = 100


@dataclass(frozen=True)
class ActivityItem:
    """파싱된 GitHub 활동 단위"""
    event_id: str
    event_type: str
    repo_name: str
    title: str
    meta: str
    occurred_at: datetime


class GithubService:
    """GitHub Public Events API 호출 및 이벤트 파싱"""

    def __init__(self) -> None:
        self.username: str = settings.GITHUB_USERNAME
        self.token: str = settings.GITHUB_PAT
        if not self.token:
            logger.warning('GITHUB_PAT가 설정되지 않아 GitHub 활동 수집이 비활성화됩니다.')

    def fetch_events(self) -> list[ActivityItem]:
        """page 1~3을 순회하며 이벤트를 수집해 ActivityItem 목록으로 반환한다.

        실패 시 빈 리스트 반환(예외 전파 금지).
        """
        items: list[ActivityItem] = []
        for page in range(1, _MAX_PAGES + 1):
            raw_events = self._request_page(page)
            if not raw_events:
                break  # 빈 페이지 또는 오류 시 중단
            for event in raw_events:
                parsed = self._parse_event(event)
                if parsed is not None:
                    items.append(parsed)
        return items

    def _request_page(self, page: int) -> list[dict]:
        url = f'{_API_BASE}/users/{self.username}/events'
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        params = {'per_page': _PER_PAGE, 'page': page}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                logger.error('GitHub Events 응답 형식 오류 (page=%s): list 아님', page)
                return []
            return data
        except requests.RequestException as e:
            logger.error('GitHub Events 요청 실패 (page=%s): %s', page, e)
            return []
        except ValueError as e:  # JSON 파싱 실패
            logger.error('GitHub Events 응답 파싱 실패 (page=%s): %s', page, e)
            return []

    def _parse_event(self, event: dict) -> ActivityItem | None:
        """단일 이벤트를 ActivityItem으로 변환한다. 필수 필드 누락 시 None."""
        event_id = event.get('id', '')
        event_type = event.get('type', '')
        repo_name = event.get('repo', {}).get('name', '')
        created_at_raw = event.get('created_at', '')
        if not event_id or not event_type or not created_at_raw:
            return None

        try:
            occurred_at = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
        except ValueError:
            return None

        title, meta = self._build_title_meta(event_type, repo_name, event.get('payload', {}))
        return ActivityItem(
            event_id=event_id,
            event_type=event_type,
            repo_name=repo_name,
            title=title,
            meta=meta,
            occurred_at=occurred_at,
        )

    def _build_title_meta(self, event_type: str, repo_name: str, payload: dict) -> tuple[str, str]:
        """이벤트 유형별 프론트 표시용 title/meta 생성 규칙"""
        if event_type == 'PushEvent':
            commits = payload.get('commits', [])
            if commits:
                message = commits[0].get('message', '')
                # 첫 줄만 사용. 메시지가 비어 있으면 "커밋"으로 폴백
                meta = message.splitlines()[0] if message else '커밋'
            else:
                meta = '커밋'  # commits 배열이 비어 있을 수 있음
            return repo_name, meta

        if event_type == 'PullRequestEvent':
            action = payload.get('action', '')
            pr_title = payload.get('pull_request', {}).get('title', '')
            return f'PR {action}', pr_title

        if event_type == 'CreateEvent':
            ref_type = payload.get('ref_type', '')
            ref = payload.get('ref') or ''
            return repo_name, f'{ref_type} 생성: {ref}'

        if event_type == 'ReleaseEvent':
            release = payload.get('release', {})
            tag_name = release.get('tag_name', '')
            name = release.get('name') or ''
            return f'{repo_name} 릴리즈', f'{tag_name} {name}'.strip()

        if event_type == 'IssuesEvent':
            action = payload.get('action', '')
            issue_title = payload.get('issue', {}).get('title', '')
            return f'이슈 {action}', issue_title

        if event_type == 'WatchEvent':
            return repo_name, '스타 추가'

        if event_type == 'ForkEvent':
            return repo_name, '포크'

        # 기타 이벤트
        return repo_name, event_type
