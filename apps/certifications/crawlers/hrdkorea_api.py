import logging
from datetime import date, datetime

import requests
from django.conf import settings
from django.utils import timezone

from .base import BaseExamCrawler, ExamRoundItem

logger = logging.getLogger(__name__)

_API_URL = 'https://apis.data.go.kr/B490007/qualExamSchd/getQualExamSchdList'
_REQUEST_TIMEOUT = 10
_ROWS_PER_PAGE = 100
_SUCCESS_RESULT_CODE = '00'


def _parse_date(value: str | None) -> date | None:
    """API 날짜 필드(YYYYMMDD)를 date로 변환한다. 값이 없거나 형식이 다르면 None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y%m%d').date()
    except ValueError:
        logger.warning('날짜 형식을 해석할 수 없습니다: %s', value)
        return None


class HrdKoreaApiCrawler(BaseExamCrawler):
    """공공데이터포털 '한국산업인력공단_국가자격 시험일정 조회 서비스' API 클라이언트.

    implYy(시행년도)가 필수 파라미터라 올해와 내년 두 해를 조회해 합친다 — 다음 해 1회차
    일정이 연말에 미리 공개되는 경우를 놓치지 않기 위함이다. 한 API 레코드는 필기·실기
    일정을 함께 담고 있어 각각 별도의 ExamRoundItem으로 분리해 반환한다.
    """

    def crawl(self, source_id: str) -> list[ExamRoundItem]:
        this_year = timezone.localdate().year
        rounds: list[ExamRoundItem] = []
        for year in (this_year, this_year + 1):
            rounds.extend(self._crawl_year(source_id, year))
        return rounds

    def _crawl_year(self, jm_cd: str, impl_yy: int) -> list[ExamRoundItem]:
        raw_rows: list[dict] = []
        page_no = 1
        while True:
            page = self._fetch_page(jm_cd, impl_yy, page_no)
            if page is None:
                break
            raw_rows.extend(page['rows'])
            if not page['rows'] or len(raw_rows) >= page['total_count']:
                break
            page_no += 1

        rounds: list[ExamRoundItem] = []
        for row in raw_rows:
            rounds.extend(self._row_to_rounds(row))
        return rounds

    def _fetch_page(self, jm_cd: str, impl_yy: int, page_no: int) -> dict | None:
        params = {
            'serviceKey': settings.HRD_KOREA_API_KEY,
            'numOfRows': _ROWS_PER_PAGE,
            'pageNo': page_no,
            'dataFormat': 'json',
            'implYy': impl_yy,
            'jmCd': jm_cd,
        }
        try:
            response = requests.get(_API_URL, params=params, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as e:
            logger.error(
                '국가자격 시험일정 API 호출 실패 (jmCd=%s, implYy=%s): %s', jm_cd, impl_yy, type(e).__name__,
            )
            return None

        envelope = payload.get('response', {})
        header = envelope.get('header', {})
        if header.get('resultCode') != _SUCCESS_RESULT_CODE:
            logger.error(
                '국가자격 시험일정 API 오류 응답 (jmCd=%s, implYy=%s): %s',
                jm_cd, impl_yy, header.get('resultMsg'),
            )
            return None

        body = envelope.get('body', {})
        raw_items = body.get('items')
        item = raw_items.get('item') if isinstance(raw_items, dict) else None
        rows = item if isinstance(item, list) else ([item] if item else [])
        return {'rows': rows, 'total_count': body.get('totalCount', len(rows))}

    def _row_to_rounds(self, row: dict) -> list[ExamRoundItem]:
        impl_yy = row.get('implYy', '')
        impl_seq = row.get('implSeq', '')
        rounds: list[ExamRoundItem] = []

        written = self._build_round(
            f'{impl_yy}년 {impl_seq}회 필기',
            row.get('docRegStartDt'), row.get('docRegEndDt'), row.get('docExamStartDt'), row.get('docPassDt'),
        )
        if written is not None:
            rounds.append(written)

        practical = self._build_round(
            f'{impl_yy}년 {impl_seq}회 실기',
            row.get('pracRegStartDt'), row.get('pracRegEndDt'), row.get('pracExamStartDt'), row.get('pracPassDt'),
        )
        if practical is not None:
            rounds.append(practical)

        return rounds

    def _build_round(
        self, round_name: str, reg_start: str | None, reg_end: str | None,
        exam_date_str: str | None, result_date_str: str | None,
    ) -> ExamRoundItem | None:
        registration_start = _parse_date(reg_start)
        registration_end = _parse_date(reg_end)
        if registration_start is None or registration_end is None:
            return None
        return ExamRoundItem(
            round_name=round_name,
            registration_start=registration_start,
            registration_end=registration_end,
            exam_date=_parse_date(exam_date_str),
            result_announcement_date=_parse_date(result_date_str),
            source_url='https://www.q-net.or.kr/crf021.do',
        )
