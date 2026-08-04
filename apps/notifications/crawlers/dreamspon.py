import logging
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from .base import BaseCrawler, BaseNoticeItem

logger = logging.getLogger(__name__)

_BASE_URL = 'https://www.dreamspon.com'
_REQUEST_TIMEOUT = 15
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}


@dataclass
class DreamsponItem(BaseNoticeItem):
    """드림스폰 장학금 아이템 (일반장학금/드림장학금 공용)"""
    organization: str | None          # 기관명
    hit_count: int | None             # 조회수
    scholarship_type: str | None      # 장학종류 (로그인 필요)
    target: str | None                # 선발대상 (로그인 필요)
    recruit_count: str | None         # 선발인원
    benefit: str | None               # 장학혜택
    application_start: date | None    # 신청기간 시작
    application_end: date | None      # 신청기간 종료
    tags: list[str] = field(default_factory=list)  # 해시태그


class DreamsponCrawler(BaseCrawler):
    """드림스폰(dreamspon.com) 장학금 목록/상세 크롤러

    대상 URL:
    https://www.dreamspon.com/scholarship/list.html (일반장학금)
    https://www.dreamspon.com/dreamscholarship/list.html (드림장학금)

    목록 페이지는 로그인 없이 전체 정보가 노출되지만, 일반장학금 상세 페이지는
    로그인 후에만 선발대상·장학종류 등이 노출되므로 상세 크롤링 시 로그인 세션을 사용한다.
    """

    def crawl(self) -> list[DreamsponItem]:
        """목록 페이지에서 DreamsponItem 목록을 반환한다."""
        try:
            response = requests.get(self.list_url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('드림스폰 목록 페이지 요청 실패: %s', e)
            return []

        return self._parse_list(response.text)

    def _parse_list(self, html: str) -> list[DreamsponItem]:
        soup = BeautifulSoup(html, 'lxml')
        items: list[DreamsponItem] = []
        seen_ids: set[str] = set()

        for row in soup.select('div.bo_table table tbody tr'):
            link_tag = row.select_one('td.td_subject p.title a')
            if not link_tag:
                continue

            href = link_tag.get('href', '')
            url = urljoin(_BASE_URL, href)
            article_id = self._extract_article_id(url)
            if not article_id or article_id in seen_ids:
                continue

            title = link_tag.get_text(strip=True)
            if not title:
                continue
            seen_ids.add(article_id)

            tds = row.find_all('td')
            organization = tds[1].get_text(strip=True) if len(tds) > 1 else None
            hit_count = self._parse_hit_count(tds[-1]) if tds else None
            tags = [
                span.get_text(strip=True)
                for span in row.select('div.hashtag span')
                if span.get_text(strip=True)
            ]

            items.append(DreamsponItem(
                article_id=article_id,
                title=title,
                url=url,
                organization=organization,
                hit_count=hit_count,
                scholarship_type=None,
                target=None,
                recruit_count=None,
                benefit=None,
                application_start=None,
                application_end=None,
                tags=tags,
            ))

        return items

    def _extract_article_id(self, url: str) -> str | None:
        query = parse_qs(urlparse(url).query)
        idx = query.get('idx')
        return idx[0] if idx else None

    def _parse_hit_count(self, td: Tag) -> int | None:
        digits = re.sub(r'[^0-9]', '', td.get_text(strip=True))
        return int(digits) if digits else None
