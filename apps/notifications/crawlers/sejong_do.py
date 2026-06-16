import logging
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from .base import BaseCrawler, BaseNoticeItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://do.sejong.ac.kr'
_REQUEST_TIMEOUT = 10
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}


@dataclass
class SejongDoItem(BaseNoticeItem):
    """세종대학교 두드림 비교과 프로그램 아이템"""
    organizer: str | None                 # 기관 (span.institution)
    application_start: datetime | None    # 신청 시작일시
    application_end: datetime | None      # 신청 종료일시
    operation_start: datetime | None      # 운영 시작일시
    operation_end: datetime | None        # 운영 종료일시


class SejongDoCrawler(BaseCrawler):
    """세종대학교 두드림 비교과 프로그램 크롤러

    대상 URL:
    https://do.sejong.ac.kr/ko/program/all/list/0/1?sort=date
    """

    def crawl(self) -> list[SejongDoItem]:
        try:
            response = requests.get(self.list_url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('두드림 프로그램 목록 요청 실패: %s', e)
            return []

        return self._parse(response.text)

    def _parse(self, html: str) -> list[SejongDoItem]:
        soup = BeautifulSoup(html, 'lxml')
        items: list[SejongDoItem] = []
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

            institution_tag = link_tag.select_one('span.institution')
            organizer = institution_tag.get_text(strip=True) if institution_tag else None

            dates = self._parse_date_layers(link_tag)
            app_start, app_end = dates.get('신청', (None, None))
            op_start, op_end = dates.get('운영', (None, None))

            items.append(SejongDoItem(
                article_id=article_id,
                title=title,
                url=full_url,
                organizer=organizer,
                application_start=app_start,
                application_end=app_end,
                operation_start=op_start,
                operation_end=op_end,
            ))

        return items

    def _parse_date_layers(self, link_tag: Tag) -> dict[str, tuple[datetime | None, datetime | None]]:
        """신청/운영 기간을 date_layer에서 파싱한다."""
        result: dict[str, tuple[datetime | None, datetime | None]] = {}
        for small in link_tag.select('small.date_layer'):
            date_title = small.select_one('span.date_title')
            if not date_title:
                continue
            key = date_title.get_text(strip=True).rstrip(':')
            times = small.select('time[datetime]')
            start = self._parse_iso_datetime(times[0]) if len(times) > 0 else None
            end = self._parse_iso_datetime(times[1]) if len(times) > 1 else None
            result[key] = (start, end)
        return result

    def _parse_iso_datetime(self, time_tag: Tag) -> datetime | None:
        try:
            return datetime.fromisoformat(time_tag['datetime'])
        except (ValueError, KeyError):
            return None
