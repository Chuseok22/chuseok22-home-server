from datetime import date, datetime
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase
from bs4 import BeautifulSoup

from apps.notifications.crawlers.dacon import DaconCrawler, DaconItem
from apps.notifications.crawlers.dreamspon import DreamsponCrawler, DreamsponItem
from apps.notifications.crawlers.dreamspon_auth import DreamsponSession
from apps.notifications.crawlers.linkareer import ContestItem, LinkareerCrawler
from apps.notifications.crawlers.sejong_do import SejongDoCrawler
from apps.notifications.crawlers.github_trending import GithubTrendingCrawler, TrendingRepoEntry
from apps.ai.models import PromptTemplate
from apps.ai.services.prompt_template import GITHUB_TRENDING_SUMMARY_FEATURE
from apps.ai.services.suh_aider_client import SuhAiderClientError


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


_DREAMSPON_SCHOLARSHIP_LIST_HTML = '''
<div class="bo_table">
<table>
<thead><tr><th>장학명</th><th>기관명</th><th>모집현황</th><th>조회</th></tr></thead>
<tbody>
<tr class="">
    <td class="td_subject">
        <p class="title"><a href="/scholarship/view.html?idx=9130">에디티지 신진 연구자 대상 에디티지 장학</a></p>
        <div class="hashtag">
            <span>#장학프로그램</span>
            <span>#기타지원</span>
            <span>#일반인</span>
        </div>
    </td>
    <td>에디티지</td>
    <td class="td_day">
        <span class="count"><span style='color:#404040;'>D-3</span></span>
        <span class="state bgRed">마감임박</span>
    </td>
    <td class="hit">1294</td>
</tr>
<tr class="">
    <td class="td_subject">
        <p class="title"><a href="/scholarship/view.html?idx=9131">보령시 학자금대출 이자지원 (2026년 상반기)</a></p>
        <div class="hashtag">
            <span>#대출지원</span>
            <span>#대학생</span>
        </div>
    </td>
    <td>보령시</td>
    <td class="td_day">
        <span class="count"><span style='color:#404040;'>D-3</span></span>
        <span class="state bgRed">마감임박</span>
    </td>
    <td class="hit">163</td>
</tr>
</tbody>
</table>
</div>
'''

_DREAMSCHOLARSHIP_LIST_HTML = '''
<div class="bo_table">
<table>
<thead><tr><th>장학명</th><th>기관명</th><th>모집현황</th><th>조회</th></tr></thead>
<tbody>
<tr class="">
    <td class="td_subject">
        <p class="title"><a href="/dreamscholarship/view.html?idx=8706">13주년 기념 제아치과 치아교정 특별 할인 혜택(8월)</a></p>
        <div class="hashtag">
            <span>#서울대출신전문의</span>
        </div>
    </td>
    <td>제아치과의원</td>
    <td class="td_day">
        <span class="count"><span style='color:#404040;'>D-27</span></span>
        <span class="state bgBlue">모집중</span>
    </td>
    <td class="td_hit">22170</td>
</tr>
</tbody>
</table>
</div>
'''


class TestDreamsponCrawlerExtractArticleId(TestCase):
    def setUp(self) -> None:
        self.crawler = DreamsponCrawler('https://www.dreamspon.com/scholarship/list.html')

    def test_scholarship_url에서_idx_추출(self) -> None:
        result = self.crawler._extract_article_id(
            'https://www.dreamspon.com/scholarship/view.html?idx=9130',
        )
        self.assertEqual(result, '9130')

    def test_dreamscholarship_url에서_idx_추출(self) -> None:
        result = self.crawler._extract_article_id(
            'https://www.dreamspon.com/dreamscholarship/view.html?idx=8706',
        )
        self.assertEqual(result, '8706')

    def test_idx_없는_경우(self) -> None:
        result = self.crawler._extract_article_id('https://www.dreamspon.com/scholarship/list.html')
        self.assertIsNone(result)


class TestDreamsponCrawlerParseList(TestCase):
    def setUp(self) -> None:
        self.crawler = DreamsponCrawler('https://www.dreamspon.com/scholarship/list.html')

    def test_일반장학금_목록_파싱(self) -> None:
        items = self.crawler._parse_list(_DREAMSPON_SCHOLARSHIP_LIST_HTML)
        self.assertEqual(len(items), 2)

        first = items[0]
        self.assertIsInstance(first, DreamsponItem)
        self.assertEqual(first.article_id, '9130')
        self.assertEqual(first.title, '에디티지 신진 연구자 대상 에디티지 장학')
        self.assertEqual(first.url, 'https://www.dreamspon.com/scholarship/view.html?idx=9130')
        self.assertEqual(first.organization, '에디티지')
        self.assertEqual(first.hit_count, 1294)
        self.assertEqual(first.tags, ['#장학프로그램', '#기타지원', '#일반인'])
        self.assertIsNone(first.scholarship_type)
        self.assertIsNone(first.application_start)

        second = items[1]
        self.assertEqual(second.article_id, '9131')
        self.assertEqual(second.organization, '보령시')
        self.assertEqual(second.hit_count, 163)

    def test_드림장학금_목록_파싱_td_hit_클래스도_지원(self) -> None:
        items = self.crawler._parse_list(_DREAMSCHOLARSHIP_LIST_HTML)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].article_id, '8706')
        self.assertEqual(items[0].organization, '제아치과의원')
        self.assertEqual(items[0].hit_count, 22170)

    def test_링크_없는_행_무시(self) -> None:
        html = '<div class="bo_table"><table><tbody><tr><td class="td_subject"></td></tr></tbody></table></div>'
        items = self.crawler._parse_list(html)
        self.assertEqual(items, [])


class TestDreamsponCrawlerCrawlRequestFailure(TestCase):
    def test_요청_실패_시_빈_리스트(self) -> None:
        crawler = DreamsponCrawler('https://www.dreamspon.com/scholarship/list.html')
        with patch('apps.notifications.crawlers.dreamspon.requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException('연결 실패')
            result = crawler.crawl()
        self.assertEqual(result, [])


_DREAMSPON_DETAIL_HTML_MASKED = '''
<html><head>
<meta property="og:title" content="에디티지 신진 연구자 대상 에디티지 장학, 드림스폰"/>
</head><body>
<div class="infoTable basic-info">
    <ul><li class="col">장학종류</li><li>*****</li></ul>
    <ul><li class="col">선발인원</li><li>총 ****명 선발</li></ul>
    <ul><li class="col">장학혜택</li><li><p>최대 *******만원</p></li></ul>
    <ul><li class="col">선발대상</li><li>******</li></ul>
    <ul><li class="col">신청기간</li><li class="day">******** ~ ********</li></ul>
</div>
</body></html>
'''

_DREAMSPON_DETAIL_HTML_LOGGED_IN = '''
<html><head>
<meta property="og:title" content="에디티지 신진 연구자 대상 에디티지 장학, 드림스폰"/>
</head><body>
<div class="infoTable basic-info">
    <ul><li class="col">장학종류</li><li>포상/상금</li></ul>
    <ul><li class="col">선발인원</li><li>총 16명</li></ul>
    <ul><li class="col">장학혜택</li><li><p>최대 1,000만원</p></li></ul>
    <ul><li class="col">선발대상</li><li>이공계열 신진 연구자</li></ul>
    <ul><li class="col">신청기간</li><li class="day">2026. 05. 26. ~ 2026. 08. 07.</li></ul>
</div>
<div id="tab2s" class="contbox">
    <dl class="scholarship04 type3">
        <dt>&middot;&nbsp;기관명</dt><dd>에디티지</dd>
        <dt>&middot;&nbsp;기관분류</dt><dd>기타</dd>
    </dl>
</div>
</body></html>
'''


class TestDreamsponCrawlerParseDetail(TestCase):
    def setUp(self) -> None:
        self.crawler = DreamsponCrawler('https://www.dreamspon.com/scholarship/list.html')
        self.url = 'https://www.dreamspon.com/scholarship/view.html?idx=9130'

    def test_로그인_전_마스킹된_상세_파싱(self) -> None:
        item = self.crawler._parse_detail(_DREAMSPON_DETAIL_HTML_MASKED, self.url)
        self.assertIsInstance(item, DreamsponItem)
        self.assertEqual(item.article_id, '9130')
        self.assertEqual(item.title, '에디티지 신진 연구자 대상 에디티지 장학')
        # 마스킹된 필드('*' 포함)는 실제 값 대신 None으로 폴백해 알림에 마스킹
        # 문자열이 그대로 노출되지 않는다
        self.assertIsNone(item.scholarship_type)
        self.assertIsNone(item.target)
        self.assertIsNone(item.recruit_count)
        self.assertIsNone(item.benefit)
        self.assertIsNone(item.application_start)
        self.assertIsNone(item.application_end)

    def test_로그인_후_상세_파싱(self) -> None:
        item = self.crawler._parse_detail(_DREAMSPON_DETAIL_HTML_LOGGED_IN, self.url)
        self.assertEqual(item.scholarship_type, '포상/상금')
        self.assertEqual(item.target, '이공계열 신진 연구자')
        self.assertEqual(item.recruit_count, '총 16명')
        self.assertEqual(item.benefit, '최대 1,000만원')
        self.assertEqual(item.application_start, date(2026, 5, 26))
        self.assertEqual(item.application_end, date(2026, 8, 7))
        self.assertEqual(item.organization, '에디티지')

    def test_og_title_없으면_None(self) -> None:
        html = '<html><head></head><body></body></html>'
        item = self.crawler._parse_detail(html, self.url)
        self.assertIsNone(item)

    def test_article_id_추출_불가시_None(self) -> None:
        item = self.crawler._parse_detail(
            _DREAMSPON_DETAIL_HTML_LOGGED_IN, 'https://www.dreamspon.com/scholarship/view.html',
        )
        self.assertIsNone(item)


_DREAMSPON_DETAIL_HTML_NO_ORG_BLOCK = '''
<html><head>
<meta property="og:title" content="에디티지 신진 연구자 대상 에디티지 장학, 드림스폰"/>
</head><body>
<div class="infoTable basic-info"></div>
</body></html>
'''


class TestDreamsponCrawlerDetailMergesListMetadata(TestCase):
    """상세 페이지에는 기관명·태그가 없거나 비어 있을 수 있어, crawl()에서 캐시한
    목록 값으로 보완되는지 검증한다 (상세 크롤링 성공 시 목록에서만 얻을 수 있는
    정보가 사라지지 않아야 한다)."""

    def setUp(self) -> None:
        self.crawler = DreamsponCrawler('https://www.dreamspon.com/scholarship/list.html')
        self.crawler._parse_list(_DREAMSPON_SCHOLARSHIP_LIST_HTML)

    def test_상세에_기관명_블록이_없으면_목록_값으로_보완(self) -> None:
        item = self.crawler._parse_detail(
            _DREAMSPON_DETAIL_HTML_NO_ORG_BLOCK,
            'https://www.dreamspon.com/scholarship/view.html?idx=9130',
        )
        self.assertEqual(item.organization, '에디티지')

    def test_상세에는_태그가_없어_목록_태그를_그대로_사용(self) -> None:
        item = self.crawler._parse_detail(
            _DREAMSPON_DETAIL_HTML_NO_ORG_BLOCK,
            'https://www.dreamspon.com/scholarship/view.html?idx=9130',
        )
        self.assertEqual(item.tags, ['#장학프로그램', '#기타지원', '#일반인'])

    def test_상세의_기관명이_있으면_상세_값을_우선한다(self) -> None:
        html_with_different_org = '''
        <html><head>
        <meta property="og:title" content="에디티지 신진 연구자 대상 에디티지 장학, 드림스폰"/>
        </head><body>
        <div class="infoTable basic-info"></div>
        <div id="tab2s" class="contbox">
            <dl class="scholarship04 type3">
                <dt>&middot;&nbsp;기관명</dt><dd>상세페이지전용기관명</dd>
            </dl>
        </div>
        </body></html>
        '''
        item = self.crawler._parse_detail(
            html_with_different_org,
            'https://www.dreamspon.com/scholarship/view.html?idx=9130',
        )
        self.assertEqual(item.organization, '상세페이지전용기관명')

    def test_목록_캐시에_없는_article_id는_빈_태그로_폴백(self) -> None:
        item = self.crawler._parse_detail(
            _DREAMSPON_DETAIL_HTML_NO_ORG_BLOCK,
            'https://www.dreamspon.com/scholarship/view.html?idx=99999',
        )
        self.assertIsNone(item.organization)
        self.assertEqual(item.tags, [])


class TestDreamsponCrawlerParseApplicationPeriod(TestCase):
    def setUp(self) -> None:
        self.crawler = DreamsponCrawler('https://www.dreamspon.com/scholarship/list.html')

    def test_정상_기간_파싱(self) -> None:
        result = self.crawler._parse_application_period('2026. 05. 26. ~ 2026. 08. 07.')
        self.assertEqual(result, (date(2026, 5, 26), date(2026, 8, 7)))

    def test_마스킹된_문자열은_None(self) -> None:
        result = self.crawler._parse_application_period('******** ~ ********')
        self.assertEqual(result, (None, None))

    def test_None_입력(self) -> None:
        result = self.crawler._parse_application_period(None)
        self.assertEqual(result, (None, None))


class TestDreamsponCrawlerGetSession(TestCase):
    def setUp(self) -> None:
        self.crawler = DreamsponCrawler('https://www.dreamspon.com/scholarship/list.html')

    def test_로그인_성공시_세션_캐싱(self) -> None:
        mock_session = MagicMock()
        with patch('apps.notifications.crawlers.dreamspon.DreamsponAuth') as mock_auth_cls:
            mock_auth_cls.return_value.login.return_value = DreamsponSession(session=mock_session)
            first = self.crawler._get_session()
            second = self.crawler._get_session()

        self.assertIs(first, mock_session)
        self.assertIs(second, mock_session)
        mock_auth_cls.return_value.login.assert_called_once()

    def test_자격증명_미설정시_None_반환_및_재시도_안함(self) -> None:
        with patch('apps.notifications.crawlers.dreamspon.DreamsponAuth') as mock_auth_cls:
            mock_auth_cls.side_effect = ValueError('no creds')
            first = self.crawler._get_session()
            second = self.crawler._get_session()

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(mock_auth_cls.call_count, 1)

    def test_로그인_실패시_None(self) -> None:
        with patch('apps.notifications.crawlers.dreamspon.DreamsponAuth') as mock_auth_cls:
            mock_auth_cls.return_value.login.return_value = None
            result = self.crawler._get_session()

        self.assertIsNone(result)


class TestDreamsponCrawlerCrawlDetailRequestFailure(TestCase):
    def test_상세_요청_실패시_None(self) -> None:
        crawler = DreamsponCrawler('https://www.dreamspon.com/scholarship/list.html')
        with patch.object(crawler, '_get_session', return_value=None):
            with patch('apps.notifications.crawlers.dreamspon.requests.get') as mock_get:
                mock_get.side_effect = requests.RequestException('연결 실패')
                result = crawler.crawl_detail('https://www.dreamspon.com/scholarship/view.html?idx=9130')

        self.assertIsNone(result)


class TestGetCrawlerDreamspon(TestCase):
    def test_dreamspon_크롤러_반환(self) -> None:
        from apps.notifications.crawlers import get_crawler
        crawler = get_crawler('dreamspon', 'https://www.dreamspon.com/scholarship/list.html')
        self.assertIsInstance(crawler, DreamsponCrawler)


_GITHUB_TRENDING_HTML = '''
<article class="Box-row">
<h2 class="h3 lh-condensed">
<a href="/PrimeIntellect-ai/prime-agent">
    PrimeIntellect-ai /
    prime-agent
</a>
</h2>
<p class="col-9 color-fg-muted my-1 pr-4">A self-improving RLM agent for coding workflows and long-running autonomous tasks.</p>
<div class="f6 color-fg-muted mt-2">
<span class="d-inline-block ml-0 mr-3">
<span class="repo-language-color" style="background-color:#3178c6"></span>
<span itemprop="programmingLanguage">TypeScript</span>
</span>
<a href="/PrimeIntellect-ai/prime-agent/stargazers" class="Link--muted d-inline-block mr-3">
7,270
</a>
<a href="/PrimeIntellect-ai/prime-agent/forks" class="Link--muted d-inline-block mr-3">
601
</a>
<span class="d-inline-block float-sm-right">
2,293 stars today
</span>
</div>
</article>
<article class="Box-row">
<h2 class="h3 lh-condensed">
<a href="/addyosmani/agent-skills">
    addyosmani /
    agent-skills
</a>
</h2>
<p class="col-9 color-fg-muted my-1 pr-4">Production-grade engineering skills for AI coding agents.</p>
<div class="f6 color-fg-muted mt-2">
<span class="d-inline-block ml-0 mr-3">
<span class="repo-language-color" style="background-color:#f1e05a"></span>
<span itemprop="programmingLanguage">JavaScript</span>
</span>
<a href="/addyosmani/agent-skills/stargazers" class="Link--muted d-inline-block mr-3">
84,122
</a>
<a href="/addyosmani/agent-skills/forks" class="Link--muted d-inline-block mr-3">
8,984
</a>
<span class="d-inline-block float-sm-right">
1,131 stars today
</span>
</div>
</article>
'''


class TestGithubTrendingCrawlerParse(TestCase):
    def setUp(self) -> None:
        self.crawler = GithubTrendingCrawler('https://github.com/trending?since=daily')

    def test_트렌딩_목록_파싱_전체_필드(self) -> None:
        entries = self.crawler._parse(_GITHUB_TRENDING_HTML)
        self.assertEqual(len(entries), 2)

        first = entries[0]
        self.assertIsInstance(first, TrendingRepoEntry)
        self.assertEqual(first.owner_repo, 'PrimeIntellect-ai/prime-agent')
        self.assertEqual(first.url, 'https://github.com/PrimeIntellect-ai/prime-agent')
        self.assertEqual(first.language, 'TypeScript')
        self.assertEqual(first.stars_today, 2293)
        self.assertEqual(first.total_stars, 7270)
        self.assertEqual(first.total_forks, 601)
        # _parse()는 AI 요약을 호출하지 않으므로 원본 설명이 그대로 summary_ko가 된다
        self.assertEqual(
            first.summary_ko,
            'A self-improving RLM agent for coding workflows and long-running autonomous tasks.',
        )

        second = entries[1]
        self.assertEqual(second.owner_repo, 'addyosmani/agent-skills')
        self.assertEqual(second.language, 'JavaScript')
        self.assertEqual(second.stars_today, 1131)
        self.assertEqual(second.total_stars, 84122)
        self.assertEqual(second.total_forks, 8984)

    def test_저장소_링크_없는_article은_무시(self) -> None:
        html = '<article class="Box-row"><p class="col-9">설명만 있음</p></article>'
        entries = self.crawler._parse(html)
        self.assertEqual(entries, [])

    def test_언어_태그_없으면_None(self) -> None:
        html = '''
        <article class="Box-row">
        <h2 class="h3 lh-condensed"><a href="/owner/repo">owner / repo</a></h2>
        </article>
        '''
        entries = self.crawler._parse(html)
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0].language)
        self.assertEqual(entries[0].total_stars, 0)
        self.assertEqual(entries[0].total_forks, 0)
        self.assertEqual(entries[0].stars_today, 0)

    def test_상위_10개까지만_파싱(self) -> None:
        rows = ''.join(
            f'<article class="Box-row"><h2 class="h3 lh-condensed">'
            f'<a href="/owner/repo{i}">owner / repo{i}</a></h2></article>'
            for i in range(15)
        )
        entries = self.crawler._parse(rows)
        self.assertEqual(len(entries), 10)
        self.assertEqual(entries[0].owner_repo, 'owner/repo0')
        self.assertEqual(entries[9].owner_repo, 'owner/repo9')


class TestGithubTrendingCrawlerCrawl(TestCase):
    def setUp(self) -> None:
        self.crawler = GithubTrendingCrawler('https://github.com/trending?since=daily')

    @patch.object(GithubTrendingCrawler, '_summarize')
    @patch('apps.notifications.crawlers.github_trending.requests.get')
    def test_요청_성공시_다이제스트_아이템_1개_반환(self, mock_get, mock_summarize) -> None:
        mock_response = MagicMock()
        mock_response.text = _GITHUB_TRENDING_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        mock_summarize.side_effect = lambda owner_repo, fallback_description: fallback_description

        items = self.crawler.crawl()

        self.assertEqual(len(items), 1)
        digest = items[0]
        self.assertEqual(len(digest.repos), 2)
        self.assertEqual(digest.url, 'https://github.com/trending?since=daily')
        self.assertIn('GitHub 트렌딩 TOP 2', digest.title)
        self.assertEqual(mock_summarize.call_count, 2)

    @patch('apps.notifications.crawlers.github_trending.requests.get')
    def test_요청_실패시_빈_리스트(self, mock_get) -> None:
        mock_get.side_effect = requests.RequestException('연결 실패')

        items = self.crawler.crawl()

        self.assertEqual(items, [])

    @patch('apps.notifications.crawlers.github_trending.requests.get')
    def test_파싱_결과_없으면_빈_리스트(self, mock_get) -> None:
        mock_response = MagicMock()
        mock_response.text = '<html><body>구조가 바뀐 페이지</body></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        items = self.crawler.crawl()

        self.assertEqual(items, [])

    @patch.object(GithubTrendingCrawler, '_summarize', return_value='AI 요약 결과')
    @patch('apps.notifications.crawlers.github_trending.requests.get')
    def test_crawl은_파싱된_각_저장소에_summarize_결과를_적용한다(self, mock_get, mock_summarize) -> None:
        mock_response = MagicMock()
        mock_response.text = _GITHUB_TRENDING_HTML
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        items = self.crawler.crawl()

        digest = items[0]
        self.assertTrue(all(repo.summary_ko == 'AI 요약 결과' for repo in digest.repos))


class TestGithubTrendingCrawlerFetchReadme(TestCase):
    def setUp(self) -> None:
        self.crawler = GithubTrendingCrawler('https://github.com/trending?since=daily')

    @patch('apps.notifications.crawlers.github_trending.requests.get')
    def test_readme_조회_성공(self, mock_get) -> None:
        mock_response = MagicMock()
        mock_response.text = '# README 원문'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = self.crawler._fetch_readme('owner/repo')

        self.assertEqual(result, '# README 원문')
        called_url = mock_get.call_args.args[0]
        self.assertEqual(called_url, 'https://api.github.com/repos/owner/repo/readme')
        called_headers = mock_get.call_args.kwargs['headers']
        self.assertEqual(called_headers['Accept'], 'application/vnd.github.raw')

    @patch('apps.notifications.crawlers.github_trending.requests.get')
    def test_readme_조회_실패시_None(self, mock_get) -> None:
        mock_get.side_effect = requests.RequestException('404')

        result = self.crawler._fetch_readme('owner/repo')

        self.assertIsNone(result)


class TestGithubTrendingCrawlerSummarize(TestCase):
    def setUp(self) -> None:
        self.crawler = GithubTrendingCrawler('https://github.com/trending?since=daily')
        PromptTemplate.objects.create(
            feature=GITHUB_TRENDING_SUMMARY_FEATURE, name='테스트 프롬프트',
            system_prompt='한국어로 요약해줘', model='functiongemma', is_active=True,
        )

    @patch('apps.notifications.crawlers.github_trending.SuhAiderClient')
    @patch.object(GithubTrendingCrawler, '_fetch_readme', return_value='# 원문 README')
    def test_readme_있고_ai_성공시_요약문_반환(self, mock_fetch_readme, mock_client_cls) -> None:
        mock_client_cls.return_value.chat.return_value = '한국어 요약 결과'

        result = self.crawler._summarize('owner/repo', '원본 설명')

        self.assertEqual(result, '한국어 요약 결과')
        mock_client_cls.return_value.chat.assert_called_once()
        _, kwargs = mock_client_cls.return_value.chat.call_args
        self.assertEqual(kwargs['model'], 'functiongemma')
        self.assertEqual(kwargs['messages'][0], {'role': 'system', 'content': '한국어로 요약해줘'})
        self.assertEqual(kwargs['messages'][1]['content'], '# 원문 README')

    @patch.object(GithubTrendingCrawler, '_fetch_readme', return_value=None)
    def test_readme_없으면_원본_설명으로_ai_요약_시도(self, mock_fetch_readme) -> None:
        with patch('apps.notifications.crawlers.github_trending.SuhAiderClient') as mock_client_cls:
            mock_client_cls.return_value.chat.return_value = '설명 기반 요약'
            result = self.crawler._summarize('owner/repo', '원본 설명')

        self.assertEqual(result, '설명 기반 요약')

    @patch.object(GithubTrendingCrawler, '_fetch_readme', return_value=None)
    def test_readme도_설명도_없으면_폴백_설명_그대로(self, mock_fetch_readme) -> None:
        result = self.crawler._summarize('owner/repo', '')
        self.assertEqual(result, '')

    @patch('apps.notifications.crawlers.github_trending.SuhAiderClient')
    @patch.object(GithubTrendingCrawler, '_fetch_readme', return_value='# 원문 README')
    def test_ai_1회_실패_후_재시도_성공(self, mock_fetch_readme, mock_client_cls) -> None:
        mock_client_cls.return_value.chat.side_effect = [
            SuhAiderClientError('일시 오류'), '재시도 성공 요약',
        ]

        result = self.crawler._summarize('owner/repo', '원본 설명')

        self.assertEqual(result, '재시도 성공 요약')
        self.assertEqual(mock_client_cls.return_value.chat.call_count, 2)

    @patch('apps.notifications.crawlers.github_trending.SuhAiderClient')
    @patch.object(GithubTrendingCrawler, '_fetch_readme', return_value='# 원문 README')
    def test_ai_2회_모두_실패시_폴백_설명(self, mock_fetch_readme, mock_client_cls) -> None:
        mock_client_cls.return_value.chat.side_effect = SuhAiderClientError('영구 오류')

        result = self.crawler._summarize('owner/repo', '원본 설명')

        self.assertEqual(result, '원본 설명')
        self.assertEqual(mock_client_cls.return_value.chat.call_count, 2)

    @patch('apps.notifications.crawlers.github_trending.SuhAiderClient')
    @patch.object(GithubTrendingCrawler, '_fetch_readme', return_value='# 원문 README')
    def test_ai_빈_응답이면_재시도_후_폴백_설명(self, mock_fetch_readme, mock_client_cls) -> None:
        mock_client_cls.return_value.chat.return_value = '   '

        result = self.crawler._summarize('owner/repo', '원본 설명')

        self.assertEqual(result, '원본 설명')
        self.assertEqual(mock_client_cls.return_value.chat.call_count, 2)

    @patch.object(GithubTrendingCrawler, '_fetch_readme', return_value='# 원문 README')
    def test_활성_프롬프트_없으면_폴백_설명(self, mock_fetch_readme) -> None:
        PromptTemplate.objects.filter(feature=GITHUB_TRENDING_SUMMARY_FEATURE).update(is_active=False)

        result = self.crawler._summarize('owner/repo', '원본 설명')

        self.assertEqual(result, '원본 설명')
        # 활성 프롬프트가 없으면 어차피 AI 요약을 시도할 수 없으므로, README 조회(GitHub API
        # 호출) 자체를 하지 않아야 한다.
        mock_fetch_readme.assert_not_called()


class TestGetCrawlerGithubTrending(TestCase):
    def test_github_trending_크롤러_반환(self) -> None:
        from apps.notifications.crawlers import get_crawler
        crawler = get_crawler('github_trending', 'https://github.com/trending?since=daily')
        self.assertIsInstance(crawler, GithubTrendingCrawler)
