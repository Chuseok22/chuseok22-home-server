from datetime import date, datetime
from unittest.mock import patch

import requests
from django.test import TestCase
from bs4 import BeautifulSoup

from apps.notifications.crawlers.dacon import DaconCrawler, DaconItem
from apps.notifications.crawlers.linkareer import ContestItem, LinkareerCrawler
from apps.notifications.crawlers.sejong_do import SejongDoCrawler


class TestLinkareerCrawlerExtractArticleId(TestCase):
    def setUp(self) -> None:
        self.crawler = LinkareerCrawler('https://linkareer.com/list/contest')

    def test_extract_article_id_정상_url(self) -> None:
        result = self.crawler._extract_article_id('https://linkareer.com/activity/311551')
        self.assertEqual(result, '311551')

    def test_extract_article_id_경로만(self) -> None:
        result = self.crawler._extract_article_id('/activity/99999')
        self.assertEqual(result, '99999')

    def test_extract_article_id_없는_경우(self) -> None:
        result = self.crawler._extract_article_id('https://linkareer.com/list/contest')
        self.assertIsNone(result)


class TestLinkareerCrawlerParseListFromNextData(TestCase):
    def setUp(self) -> None:
        self.crawler = LinkareerCrawler('https://linkareer.com/list/contest')

    def test_빈_activities(self) -> None:
        data = {'props': {'pageProps': {'activityList': {'activities': []}}}}
        result = self.crawler._parse_list_from_next_data(data)
        self.assertEqual(result, [])

    def test_잘못된_구조(self) -> None:
        data = {'unexpected': 'structure'}
        result = self.crawler._parse_list_from_next_data(data)
        self.assertEqual(result, [])


class TestLinkareerCrawlerParseDateStr(TestCase):
    def setUp(self) -> None:
        self.crawler = LinkareerCrawler('https://linkareer.com/list/contest')

    def test_iso_날짜_파싱(self) -> None:
        result = self.crawler._parse_date_str('2025-06-30')
        self.assertEqual(result, date(2025, 6, 30))

    def test_iso_datetime_파싱(self) -> None:
        result = self.crawler._parse_date_str('2025-06-30T23:59:59')
        self.assertEqual(result, date(2025, 6, 30))

    def test_None_입력(self) -> None:
        result = self.crawler._parse_date_str(None)
        self.assertIsNone(result)

    def test_잘못된_형식(self) -> None:
        result = self.crawler._parse_date_str('invalid-date')
        self.assertIsNone(result)


class TestSejongDoCrawlerParseIsoDatetime(TestCase):
    def setUp(self) -> None:
        self.crawler = SejongDoCrawler('https://do.sejong.ac.kr/ko/program/all/list/0/1?sort=date')

    def test_유효한_datetime_파싱(self) -> None:
        html = '<time datetime="2025-06-01T09:00:00"></time>'
        soup = BeautifulSoup(html, 'lxml')
        time_tag = soup.find('time')
        result = self.crawler._parse_iso_datetime(time_tag)
        self.assertEqual(result, datetime(2025, 6, 1, 9, 0, 0))

    def test_datetime_속성_없음(self) -> None:
        html = '<time></time>'
        soup = BeautifulSoup(html, 'lxml')
        time_tag = soup.find('time')
        result = self.crawler._parse_iso_datetime(time_tag)
        self.assertIsNone(result)


_DACON_LIST_HTML = '''
<div class="official-comp">
<div class="competetion">
<div class="comp"><a href="/competitions/official/236727/overview/" class="clearfix">
<div class="desc"><p class="name ellipsis">제3회 풍력발전량 예측 AI 경진대회 - BARAM 2026</p>
<p class="info2 ellipsis keyword"><span>알고리즘 | 사전 워크샵 | 정형 | 회귀 | 에너지</span></p></div>
<div class="etc"><div class="dday"><img src="/img/participating.jpg" alt="participating">  참가신청중
</div> <div class="joinTeam"><!---->
  1,305명
</div></div></a></div>
<div class="comp"><a href="/competitions/official/236730/overview/" class="clearfix">
<div class="desc"><p class="name ellipsis">2026 Samsung Collegiate Programming Challenge : AI 챌린지</p>
<p class="info2 ellipsis keyword"><span>채용 | SCPC | 알고리즘</span></p></div>
<div class="etc"><div class="dday"><img src="/img/non-participating.jpg" alt="non participating">  참가신청 마감
</div> <div class="joinTeam"><!---->
  1,845명
</div></div></a></div>
</div>
</div>
'''


class TestDaconCrawlerExtractArticleId(TestCase):
    def setUp(self) -> None:
        self.crawler = DaconCrawler('https://dacon.io/competitions')

    def test_extract_article_id_정상_href(self) -> None:
        result = self.crawler._extract_article_id('/competitions/official/236727/overview/')
        self.assertEqual(result, '236727')

    def test_extract_article_id_없는_경우(self) -> None:
        result = self.crawler._extract_article_id('/competitions')
        self.assertIsNone(result)


class TestDaconCrawlerParseParticipantCount(TestCase):
    def setUp(self) -> None:
        self.crawler = DaconCrawler('https://dacon.io/competitions')

    def test_콤마_포함_숫자_파싱(self) -> None:
        html = '<div class="comp"><div class="joinTeam">1,305명</div></div>'
        soup = BeautifulSoup(html, 'lxml')
        comp = soup.select_one('div.comp')
        result = self.crawler._parse_participant_count(comp)
        self.assertEqual(result, 1305)

    def test_joinTeam_태그_없는_경우(self) -> None:
        html = '<div class="comp"></div>'
        soup = BeautifulSoup(html, 'lxml')
        comp = soup.select_one('div.comp')
        result = self.crawler._parse_participant_count(comp)
        self.assertIsNone(result)


class TestDaconCrawlerParseStatus(TestCase):
    def setUp(self) -> None:
        self.crawler = DaconCrawler('https://dacon.io/competitions')

    def test_상태_텍스트_추출(self) -> None:
        html = (
            '<div class="comp"><div class="dday">'
            '<img src="/img/participating.jpg" alt="participating">  참가신청중'
            '</div></div>'
        )
        soup = BeautifulSoup(html, 'lxml')
        comp = soup.select_one('div.comp')
        result = self.crawler._parse_status(comp)
        self.assertEqual(result, '참가신청중')

    def test_dday_태그_없는_경우(self) -> None:
        html = '<div class="comp"></div>'
        soup = BeautifulSoup(html, 'lxml')
        comp = soup.select_one('div.comp')
        result = self.crawler._parse_status(comp)
        self.assertIsNone(result)


class TestDaconCrawlerParseTags(TestCase):
    def setUp(self) -> None:
        self.crawler = DaconCrawler('https://dacon.io/competitions')

    def test_파이프_구분_태그_파싱(self) -> None:
        html = (
            '<div class="comp"><p class="info2 ellipsis keyword">'
            '<span>알고리즘 | 멀티모달 | LLM</span></p></div>'
        )
        soup = BeautifulSoup(html, 'lxml')
        comp = soup.select_one('div.comp')
        result = self.crawler._parse_tags(comp)
        self.assertEqual(result, ['알고리즘', '멀티모달', 'LLM'])

    def test_keyword_태그_없는_경우(self) -> None:
        html = '<div class="comp"></div>'
        soup = BeautifulSoup(html, 'lxml')
        comp = soup.select_one('div.comp')
        result = self.crawler._parse_tags(comp)
        self.assertEqual(result, [])


class TestDaconCrawlerParse(TestCase):
    def setUp(self) -> None:
        self.crawler = DaconCrawler('https://dacon.io/competitions')

    def test_목록_파싱_전체_필드(self) -> None:
        items = self.crawler._parse(_DACON_LIST_HTML)
        self.assertEqual(len(items), 2)

        first = items[0]
        self.assertIsInstance(first, DaconItem)
        self.assertEqual(first.article_id, '236727')
        self.assertEqual(first.title, '제3회 풍력발전량 예측 AI 경진대회 - BARAM 2026')
        self.assertEqual(first.url, 'https://dacon.io/competitions/official/236727/overview/')
        self.assertEqual(first.status, '참가신청중')
        self.assertEqual(first.participant_count, 1305)
        self.assertEqual(first.tags, ['알고리즘', '사전 워크샵', '정형', '회귀', '에너지'])

        second = items[1]
        self.assertEqual(second.article_id, '236730')
        self.assertEqual(second.status, '참가신청 마감')
        self.assertEqual(second.participant_count, 1845)

    def test_href_없는_a_태그_무시(self) -> None:
        html = '<div class="comp"><a class="clearfix"><p class="name">제목만</p></a></div>'
        items = self.crawler._parse(html)
        self.assertEqual(items, [])

    def test_제목_없는_카드_무시(self) -> None:
        html = '<div class="comp"><a href="/competitions/official/1/overview/"></a></div>'
        items = self.crawler._parse(html)
        self.assertEqual(items, [])


class TestDaconCrawlerCrawlRequestFailure(TestCase):
    def test_요청_실패_시_빈_리스트(self) -> None:
        crawler = DaconCrawler('https://dacon.io/competitions')
        with patch('apps.notifications.crawlers.dacon.requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException('연결 실패')
            result = crawler.crawl()
        self.assertEqual(result, [])


class TestGetCrawlerDacon(TestCase):
    def test_dacon_크롤러_반환(self) -> None:
        from apps.notifications.crawlers import get_crawler
        crawler = get_crawler('dacon', 'https://dacon.io/competitions')
        self.assertIsInstance(crawler, DaconCrawler)
