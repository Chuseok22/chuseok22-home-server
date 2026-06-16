import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseCrawler, BaseNoticeItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://linkareer.com'
_REQUEST_TIMEOUT = 15
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}


@dataclass
class ContestItem(BaseNoticeItem):
    """링커리어 공모전 아이템"""
    company_type: str | None        # 기업형태
    target: str | None              # 참여대상
    prize: str | None               # 시상규모
    application_start: date | None  # 접수 시작일
    application_end: date | None    # 접수 마감일
    homepage: str | None            # 홈페이지
    benefit: str | None             # 활동혜택
    categories: list[str] = field(default_factory=list)  # 공모분야


class LinkareerCrawler(BaseCrawler):
    """링커리어 공모전 크롤러

    대상 URL:
    https://linkareer.com/list/contest
    """

    def crawl(self) -> list[ContestItem]:
        """목록 페이지에서 article_id, title, url만 채운 ContestItem 목록을 반환한다."""
        try:
            response = requests.get(self.list_url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('링커리어 목록 페이지 요청 실패: %s', e)
            return []

        soup = BeautifulSoup(response.text, 'lxml')

        # __NEXT_DATA__ JSON 파싱 시도
        script = soup.find('script', id='__NEXT_DATA__')
        if script and script.string:
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError as e:
                logger.warning('__NEXT_DATA__ JSON 디코딩 실패, HTML fallback 사용: %s', e)
                data = None
            if data:
                items = self._parse_list_from_next_data(data)
                if items:
                    return items

        # HTML fallback
        return self._parse_list_from_html(soup)

    def crawl_detail(self, url: str) -> ContestItem | None:
        """상세 페이지에서 전체 필드를 채운 ContestItem을 반환한다."""
        try:
            response = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('링커리어 상세 페이지 요청 실패 (%s): %s', url, e)
            return None

        soup = BeautifulSoup(response.text, 'lxml')

        # __NEXT_DATA__ JSON 파싱 시도
        script = soup.find('script', id='__NEXT_DATA__')
        if script and script.string:
            try:
                data = json.loads(script.string)
            except json.JSONDecodeError as e:
                logger.warning('상세 __NEXT_DATA__ JSON 디코딩 실패, HTML fallback 사용: %s', e)
                data = None
            if data:
                item = self._parse_detail_from_next_data(data, url)
                if item:
                    return item

        # HTML fallback
        return self._parse_detail_from_html(soup, url)

    # ── 목록 파싱 ──────────────────────────────────────────────

    def _parse_list_from_next_data(self, data: dict) -> list[ContestItem]:
        """__NEXT_DATA__ JSON의 __APOLLO_STATE__에서 공모전 목록을 추출한다.

        링커리어는 Apollo Client를 사용하며, 데이터는 __APOLLO_STATE__에
        'Activity:숫자' 형태의 키로 플랫하게 저장된다.
        """
        try:
            page_props = data.get('props', {}).get('pageProps', {})
            apollo_state = page_props.get('__APOLLO_STATE__', {})
            if not apollo_state:
                return []

            items = []
            seen_ids: set[str] = set()
            for key, activity in apollo_state.items():
                if not key.startswith('Activity:'):
                    continue
                if not isinstance(activity, dict):
                    continue
                # activityTypeID=3이 공모전 타입
                if activity.get('activityTypeID') != 3:
                    continue

                aid = str(activity.get('id', ''))
                title = activity.get('title', '')
                if not aid or not title or aid in seen_ids:
                    continue
                seen_ids.add(aid)
                items.append(ContestItem(
                    article_id=aid,
                    title=title,
                    url=f'{_BASE_URL}/activity/{aid}',
                    company_type=None,
                    target=None,
                    prize=None,
                    application_start=None,
                    application_end=None,
                    homepage=None,
                    benefit=None,
                    categories=[],
                ))
            return items
        except (KeyError, TypeError, AttributeError):
            return []

    def _parse_list_from_html(self, soup: BeautifulSoup) -> list[ContestItem]:
        """HTML에서 직접 공모전 링크를 추출한다 (fallback)."""
        items = []
        seen_ids: set[str] = set()
        for a in soup.select('a[href*="/activity/"]'):
            href = a.get('href', '')
            article_id = self._extract_article_id(href)
            if not article_id or article_id in seen_ids:
                continue
            seen_ids.add(article_id)
            title = a.get_text(strip=True)
            if not title:
                continue
            items.append(ContestItem(
                article_id=article_id,
                title=title,
                url=f'{_BASE_URL}/activity/{article_id}',
                company_type=None,
                target=None,
                prize=None,
                application_start=None,
                application_end=None,
                homepage=None,
                benefit=None,
                categories=[],
            ))
        return items

    # ── 상세 파싱 ─────────────────────────────────────────────

    def _parse_detail_from_next_data(self, data: dict, url: str) -> ContestItem | None:
        """상세 페이지 __NEXT_DATA__ JSON에서 필드를 추출한다."""
        try:
            page_props = data.get('props', {}).get('pageProps', {})
            activity = (
                page_props.get('activity')
                or page_props.get('data', {}).get('activity')
            )
            if not activity:
                return None

            article_id = self._extract_article_id(url)
            if not article_id:
                return None

            title = activity.get('title', '')
            if not title.strip():
                return None
            app_start = self._parse_date_str(activity.get('applicationStartAt') or activity.get('startDate'))
            app_end = self._parse_date_str(activity.get('applicationEndAt') or activity.get('endDate'))
            categories = [c.get('name', '') for c in activity.get('categories', []) if c.get('name')]

            return ContestItem(
                article_id=article_id,
                title=title,
                url=url,
                company_type=activity.get('companyType') or activity.get('organizationType'),
                target=activity.get('target') or activity.get('targetDescription'),
                prize=activity.get('prize') or activity.get('reward'),
                application_start=app_start,
                application_end=app_end,
                homepage=activity.get('homepage') or activity.get('officialUrl'),
                benefit=activity.get('benefit') or activity.get('benefits'),
                categories=categories,
            )
        except (KeyError, TypeError, AttributeError):
            return None

    def _parse_detail_from_html(self, soup: BeautifulSoup, url: str) -> ContestItem | None:
        """상세 페이지 HTML에서 직접 필드를 추출한다 (fallback)."""
        article_id = self._extract_article_id(url)
        if not article_id:
            return None

        title_tag = soup.select_one('h1')
        title = title_tag.get_text(strip=True) if title_tag else ''
        if not title:
            return None

        def find_dd(label: str) -> str | None:
            for dt in soup.select('dt'):
                if label in dt.get_text(strip=True):
                    dd = dt.find_next_sibling('dd')
                    return dd.get_text(strip=True) if dd else None
            return None

        app_start = self._parse_date_span(soup, 'start-at')
        app_end = self._parse_date_span(soup, 'end-at')
        categories = [
            p.get_text(strip=True)
            for p in soup.select('p')
            if p.get_text(strip=True) and 'CategoryChipList' in str(p.parent.get('class', []))
        ]

        return ContestItem(
            article_id=article_id,
            title=title,
            url=url,
            company_type=find_dd('기업형태'),
            target=find_dd('참여대상'),
            prize=find_dd('시상규모'),
            application_start=app_start,
            application_end=app_end,
            homepage=find_dd('홈페이지'),
            benefit=find_dd('활동혜택'),
            categories=categories,
        )

    # ── 공통 유틸 ─────────────────────────────────────────────

    def _extract_article_id(self, url: str) -> str | None:
        match = re.search(r'/activity/(\d+)', url)
        return match.group(1) if match else None

    def _parse_date_span(self, soup: BeautifulSoup, class_name: str) -> date | None:
        span = soup.select_one(f'span.{class_name}')
        if not span:
            return None
        next_span = span.find_next_sibling('span')
        if not next_span:
            return None
        try:
            text = next_span.get_text(strip=True)
            return date(*[int(p) for p in text.split('.')])
        except (ValueError, TypeError):
            return None

    def _parse_date_str(self, value: str | None) -> date | None:
        if not value:
            return None
        try:
            # ISO 8601 형식 (2025-01-01 또는 2025-01-01T00:00:00)
            return date.fromisoformat(value[:10])
        except (ValueError, TypeError):
            return None
