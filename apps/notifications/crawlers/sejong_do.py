import logging
from datetime import date, datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from .base import BaseCrawler, NoticeItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://do.sejong.ac.kr'
_REQUEST_TIMEOUT = 10
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}


class SejongDoCrawler(BaseCrawler):
    """세종대학교 두드림 비교과 프로그램 크롤러

    대상 URL:
    https://do.sejong.ac.kr/ko/program/all/list/0/1?sort=date
    """

    def crawl(self) -> list[NoticeItem]:
        try:
            response = requests.get(self.list_url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('두드림 프로그램 목록 요청 실패: %s', e)
            return []

        return self._parse(response.text)

    def _parse(self, html: str) -> list[NoticeItem]:
        soup = BeautifulSoup(html, 'lxml')
        items: list[NoticeItem] = []
        seen_ids: set[str] = set()

        for link_tag in soup.select('a[href*="/ko/program/all/view/"]'):
            article_id = link_tag.get('data-idx', '')
            if not article_id or article_id in seen_ids:
                continue
            seen_ids.add(article_id)

            title_tag = link_tag.select_one('b.title')
            title = title_tag.get_text(strip=True) if title_tag else ''
            if not title:
                continue

            href = link_tag.get('href', '')
            full_url = urljoin(_BASE_URL, href)
            published_at = self._parse_operation_date(link_tag)

            items.append(NoticeItem(
                article_id=article_id,
                title=title,
                url=full_url,
                published_at=published_at,
            ))

        return items

    def _parse_operation_date(self, link_tag: Tag) -> date | None:
        """운영 시작일을 datetime 속성에서 추출한다."""
        for small in link_tag.select('small.date_layer'):
            date_title = small.select_one('span.date_title')
            if not date_title or '운영' not in date_title.get_text():
                continue
            time_tag = small.select_one('time[datetime]')
            if not time_tag:
                continue
            try:
                return datetime.fromisoformat(time_tag['datetime']).date()
            except (ValueError, KeyError):
                return None
        return None
