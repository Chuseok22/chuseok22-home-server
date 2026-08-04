import logging
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from .dreamspon_auth import DreamsponAuth
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

    def __init__(self, list_url: str) -> None:
        super().__init__(list_url)
        self._session: requests.Session | None = None
        self._login_attempted = False

    def crawl_detail(self, url: str) -> DreamsponItem | None:
        """상세 페이지에서 전체 필드를 채운 DreamsponItem을 반환한다.

        로그인 세션이 있으면 인증된 상태로, 없으면(자격증명 미설정/로그인 실패)
        비로그인 상태로 요청한다. 비로그인 상태에서도 이 메서드는 None이 아닌
        정상 아이템을 반환한다 — 다만 dreamspon.com이 비로그인 시 장학종류·선발대상·
        선발인원·장학혜택·신청기간 값을 '*' 마스킹 문자열로 내려주므로, _parse_detail에서
        마스킹된 값을 감지해 해당 필드를 None으로 치환한다. None을 반환하는 경우는
        요청 자체가 실패했거나(crawl_detail) og:title/article_id를 파싱할 수 없을 때뿐이다.
        """
        session = self._get_session()
        requester = session if session is not None else requests
        try:
            response = requester.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('드림스폰 상세 페이지 요청 실패 (%s): %s', url, e)
            return None

        return self._parse_detail(response.text, url)

    def _get_session(self) -> requests.Session | None:
        """로그인 세션을 반환한다. 최초 1회만 로그인을 시도하고, 실패해도 재시도하지 않는다."""
        if self._session is not None:
            return self._session
        if self._login_attempted:
            return None

        self._login_attempted = True
        try:
            auth = DreamsponAuth()
        except ValueError as e:
            logger.warning('드림스폰 로그인 자격증명 미설정, 비로그인으로 진행: %s', e)
            return None

        result = auth.login()
        if result is None:
            return None

        self._session = result.session
        return self._session

    def _parse_detail(self, html: str, url: str) -> DreamsponItem | None:
        soup = BeautifulSoup(html, 'lxml')

        article_id = self._extract_article_id(url)
        if not article_id:
            return None

        title = self._parse_title(soup)
        if not title:
            return None

        fields = self._parse_info_table(soup)
        app_start, app_end = self._parse_application_period(fields.get('신청기간'))

        return DreamsponItem(
            article_id=article_id,
            title=title,
            url=url,
            organization=self._parse_organization(soup),
            hit_count=None,
            scholarship_type=self._unmask(fields.get('장학종류')),
            target=self._unmask(fields.get('선발대상')),
            recruit_count=self._unmask(fields.get('선발인원')),
            benefit=self._unmask(fields.get('장학혜택')),
            application_start=app_start,
            application_end=app_end,
            tags=[],
        )

    def _parse_title(self, soup: BeautifulSoup) -> str:
        meta = soup.find('meta', attrs={'property': 'og:title'})
        if not meta or not meta.get('content'):
            return ''
        return re.sub(r',\s*드림스폰\s*$', '', meta['content']).strip()

    def _parse_info_table(self, soup: BeautifulSoup) -> dict[str, str]:
        fields: dict[str, str] = {}
        for ul in soup.select('div.infoTable.basic-info ul'):
            li_tags = ul.find_all('li')
            if len(li_tags) < 2:
                continue
            label = li_tags[0].get_text(strip=True)
            value = li_tags[1].get_text(strip=True)
            fields[label] = value
        return fields

    def _unmask(self, value: str | None) -> str | None:
        """비로그인 상태의 dreamspon.com이 값을 '*' 문자로 가려서 내려주는 경우
        (예: '*****', '총 ****명 선발') 그대로 노출하면 알림에 마스킹 문자열이
        그대로 섞여나가므로, '*'가 포함된 값은 미확보로 간주해 None으로 치환한다.
        """
        if value is None or '*' in value:
            return None
        return value

    def _parse_organization(self, soup: BeautifulSoup) -> str | None:
        for dt in soup.select('dl.scholarship04.type3 dt'):
            if '기관명' in dt.get_text(strip=True):
                dd = dt.find_next_sibling('dd')
                return dd.get_text(strip=True) if dd else None
        return None

    def _parse_application_period(self, text: str | None) -> tuple[date | None, date | None]:
        if not text:
            return None, None
        match = re.search(
            r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*~\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?',
            text,
        )
        if not match:
            return None, None
        y1, m1, d1, y2, m2, d2 = match.groups()
        try:
            return date(int(y1), int(m1), int(d1)), date(int(y2), int(m2), int(d2))
        except ValueError:
            return None, None
