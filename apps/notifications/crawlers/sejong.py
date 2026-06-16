import logging
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .base import BaseCrawler, BaseNoticeItem

logger = logging.getLogger(__name__)

# 세종대학교 공지사항 페이지 기본 도메인
_BASE_DOMAIN = 'https://www.sejong.ac.kr'
_REQUEST_TIMEOUT = 10
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}


@dataclass
class SejongNoticeItem(BaseNoticeItem):
    """세종대학교 공지사항 아이템"""
    published_at: date | None


class SejongNoticeCrawler(BaseCrawler):
    """세종대학교 공지사항 크롤러

    대상 URL 예시:
    https://www.sejong.ac.kr/kor/intro/notice3.do?mode=list&article.offset=0&articleLimit=10
    """

    def crawl(self) -> list[SejongNoticeItem]:
        try:
            response = requests.get(self.list_url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('세종대 공지 목록 요청 실패: %s', e)
            return []

        return self._parse(response.text)

    def _parse(self, html: str) -> list[SejongNoticeItem]:
        soup = BeautifulSoup(html, 'lxml')
        items: list[SejongNoticeItem] = []
        seen_ids: set[str] = set()

        for row in soup.select('tbody tr'):
            link_tag = row.select_one('a[href*="articleNo"]')
            if not link_tag:
                continue

            href = link_tag.get('href', '')
            article_id = self._extract_article_id(href)
            if not article_id or article_id in seen_ids:
                continue
            seen_ids.add(article_id)

            title_tag = link_tag.select_one('span.b-title')
            title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
            if not title:
                continue

            full_url = self._build_detail_url(href)
            published_at = self._parse_date(row)

            items.append(SejongNoticeItem(
                article_id=article_id,
                title=title,
                url=full_url,
                published_at=published_at,
            ))

        return items

    def _extract_article_id(self, href: str) -> str | None:
        match = re.search(r'articleNo=(\d+)', href)
        return match.group(1) if match else None

    def _build_detail_url(self, href: str) -> str:
        # href가 절대경로이면 그대로, 상대경로이면 base domain 기준으로 조합
        parsed = urlparse(href)
        if parsed.scheme:
            return href
        base_path = urlparse(self.list_url).path
        return urljoin(f'{_BASE_DOMAIN}{base_path}', href)

    def _parse_date(self, row: BeautifulSoup) -> date | None:
        date_tag = row.select_one('span.b-date')
        if not date_tag:
            return None
        try:
            return date(*[int(p) for p in date_tag.get_text(strip=True).split('.')])
        except (ValueError, TypeError):
            return None
