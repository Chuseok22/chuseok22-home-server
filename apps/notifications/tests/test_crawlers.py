from datetime import date, datetime
from django.test import TestCase
from bs4 import BeautifulSoup

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
