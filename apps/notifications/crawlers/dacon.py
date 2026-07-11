import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from .base import BaseCrawler, BaseNoticeItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://dacon.io'
_REQUEST_TIMEOUT = 15
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}


@dataclass
class DaconItem(BaseNoticeItem):
    """데이콘 경진대회 아이템 (목록 페이지 정보만 포함 — 상세 페이지는 JS 렌더링 필요로 미지원)"""
    status: str | None                # 참가신청중 / 참가신청 마감 / 연습 등 상태 배지 텍스트
    participant_count: int | None     # 참가자 수
    tags: list[str] = field(default_factory=list)  # 키워드 태그 목록


class DaconCrawler(BaseCrawler):
    """데이콘 경진대회 목록 크롤러

    대상 URL:
    https://dacon.io/competitions
    """

    def crawl(self) -> list[DaconItem]:
        """목록 페이지에서 DaconItem 목록을 반환한다."""
        try:
            response = requests.get(self.list_url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('데이콘 목록 페이지 요청 실패: %s', e)
            return []

        return self._parse(response.text)

    def _parse(self, html: str) -> list[DaconItem]:
        soup = BeautifulSoup(html, 'lxml')
        items: list[DaconItem] = []
        seen_ids: set[str] = set()

        for comp in soup.select('div.comp'):
            link_tag = comp.select_one('a[href*="/competitions/official/"]')
            if not link_tag:
                continue

            href = link_tag.get('href', '')
            article_id = self._extract_article_id(href)
            if not article_id or article_id in seen_ids:
                continue

            title_tag = comp.select_one('p.name')
            title = title_tag.get_text(strip=True) if title_tag else ''
            if not title:
                continue
            seen_ids.add(article_id)

            items.append(DaconItem(
                article_id=article_id,
                title=title,
                url=urljoin(_BASE_URL, href),
                status=self._parse_status(comp),
                participant_count=self._parse_participant_count(comp),
                tags=self._parse_tags(comp),
            ))

        return items

    def _extract_article_id(self, href: str) -> str | None:
        match = re.search(r'/competitions/official/(\d+)', href)
        return match.group(1) if match else None

    def _parse_status(self, comp: Tag) -> str | None:
        dday_tag = comp.select_one('div.dday')
        if not dday_tag:
            return None
        text = dday_tag.get_text(strip=True)
        return text or None

    def _parse_participant_count(self, comp: Tag) -> int | None:
        join_team_tag = comp.select_one('div.joinTeam')
        if not join_team_tag:
            return None
        digits = re.sub(r'[^0-9]', '', join_team_tag.get_text(strip=True))
        return int(digits) if digits else None

    def _parse_tags(self, comp: Tag) -> list[str]:
        keyword_tag = comp.select_one('p.info2.keyword span')
        if not keyword_tag:
            return []
        text = keyword_tag.get_text(strip=True)
        return [tag.strip() for tag in text.split('|') if tag.strip()]
