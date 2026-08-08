import logging
import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup, Tag
from django.utils import timezone

from .base import BaseCrawler, BaseNoticeItem

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; chuseok22-home-server/1.0)',
}
_TOP_N = 10


@dataclass(frozen=True)
class TrendingRepoEntry:
    """트렌딩 저장소 1건의 정보"""
    owner_repo: str
    url: str
    language: str | None
    stars_today: int
    total_stars: int
    total_forks: int
    summary_ko: str


@dataclass
class GithubTrendingDigestItem(BaseNoticeItem):
    """그날의 트렌딩 TOP N을 담은 단일 다이제스트 아이템"""
    repos: list[TrendingRepoEntry] = field(default_factory=list)


class GithubTrendingCrawler(BaseCrawler):
    """github.com/trending 스크래핑 + 저장소별 README 한국어 요약을 더한 일일 다이제스트 크롤러

    대상 URL:
    https://github.com/trending?since=daily
    """

    def crawl(self) -> list[BaseNoticeItem]:
        try:
            response = requests.get(self.list_url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('GitHub 트렌딩 페이지 요청 실패: %s', e)
            return []

        entries = self._parse(response.text)
        if not entries:
            logger.error('GitHub 트렌딩 페이지 파싱 결과가 비어있습니다 (HTML 구조 변경 가능성)')
            return []

        today = timezone.localdate()
        digest = GithubTrendingDigestItem(
            article_id=today.isoformat(),
            title=f'GitHub 트렌딩 TOP {len(entries)} ({today.strftime("%Y.%m.%d")})',
            url=self.list_url,
            repos=entries,
        )
        return [digest]

    def _parse(self, html: str) -> list[TrendingRepoEntry]:
        soup = BeautifulSoup(html, 'lxml')
        entries: list[TrendingRepoEntry] = []

        for row in soup.select('article.Box-row')[:_TOP_N]:
            owner_repo = self._parse_owner_repo(row)
            if not owner_repo:
                continue
            description = self._parse_description(row)
            entries.append(TrendingRepoEntry(
                owner_repo=owner_repo,
                url=f'https://github.com/{owner_repo}',
                language=self._parse_language(row),
                stars_today=self._parse_count_suffix(row, 'span.d-inline-block.float-sm-right'),
                total_stars=self._parse_count_href(row, '/stargazers'),
                total_forks=self._parse_count_href(row, '/forks'),
                summary_ko=description,
            ))
        return entries

    def _parse_owner_repo(self, row: Tag) -> str | None:
        link = row.select_one('h2.h3.lh-condensed a')
        if not link:
            return None
        href = (link.get('href') or '').strip('/')
        return href or None

    def _parse_description(self, row: Tag) -> str:
        desc_tag = row.select_one('p.col-9')
        return desc_tag.get_text(strip=True) if desc_tag else ''

    def _parse_language(self, row: Tag) -> str | None:
        lang_tag = row.select_one('span[itemprop="programmingLanguage"]')
        return lang_tag.get_text(strip=True) if lang_tag else None

    def _parse_count_href(self, row: Tag, href_suffix: str) -> int:
        link = row.select_one(f'a[href$="{href_suffix}"]')
        if not link:
            return 0
        return self._digits_to_int(link.get_text(strip=True))

    def _parse_count_suffix(self, row: Tag, selector: str) -> int:
        tag = row.select_one(selector)
        if not tag:
            return 0
        return self._digits_to_int(tag.get_text(strip=True))

    def _digits_to_int(self, text: str) -> int:
        digits = re.sub(r'[^0-9]', '', text)
        return int(digits) if digits else 0
