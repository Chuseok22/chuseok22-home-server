import json
import logging
from dataclasses import dataclass
from typing import Literal

import requests

from apps.sejong.student.services.classic_auth import SejongClassicAuthService

logger = logging.getLogger(__name__)

_SEARCH_URL = 'https://classic.sejong.ac.kr/classic/creative/register/userSearch.do'
_REQUEST_TIMEOUT = 15

# Classic 학생 조회 API가 허용하는 검색 카테고리
_SearchCategory = Literal['userName', 'userId']


@dataclass(frozen=True)
class StudentInfo:
    student_no: str
    name: str
    dept_cd: str
    dept_name: str
    email: str | None  # Classic API에서 email 필드 누락 가능
    double_dept_name: str | None


class StudentSearchService:
    """세종대학교 Classic 학생 조회 서비스.

    category=userName: 이름 검색 (동명이인 다수 반환 가능)
    category=userId: 학번 검색 (단일 결과)

    반환값: None=외부 서비스 장애, []=결과 없음, [...]=정상 결과
    """

    def __init__(self, auth: SejongClassicAuthService | None = None) -> None:
        # 테스트 시 mock 주입 가능하도록 의존성 주입 패턴 적용
        self._auth = auth or SejongClassicAuthService()

    def search_by_name(self, name: str) -> list[StudentInfo] | None:
        """이름으로 학생 검색. 장애 시 None, 결과 없음 시 []."""
        return self._search(category='userName', search_value=name)

    def search_by_student_no(self, student_no: str) -> list[StudentInfo] | None:
        """학번으로 학생 검색. 장애 시 None, 결과 없음 시 []."""
        return self._search(category='userId', search_value=student_no)

    def _search(self, category: _SearchCategory, search_value: str) -> list[StudentInfo] | None:
        session = self._auth.create_session()
        if session is None:
            logger.error('classic.sejong.ac.kr 세션 획득 실패 — 학생 조회 불가')
            return None  # 장애 — 뷰에서 503 반환

        try:
            resp = session.post(
                _SEARCH_URL,
                data={'category': category, 'searchValue': search_value},
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            # search_value(학번·이름)는 PII이므로 로그에서 제외
            logger.error('학생 조회 요청 실패 (category=%s): %s', category, e)
            return None  # 장애 — 뷰에서 503 반환
        except (requests.exceptions.JSONDecodeError, json.JSONDecodeError) as e:
            # 200이지만 HTML 반환(세션 만료 등) → JSON 파싱 실패
            logger.error('학생 조회 응답 파싱 실패 — 세션 만료 가능성: %s', e)
            return None  # 장애 — 뷰에서 503 반환

        results = []
        for user in data.get('userList', []):
            try:
                results.append(StudentInfo(
                    student_no=user['studentNo'],
                    name=user['nm'],
                    dept_cd=user['deptCd'],
                    dept_name=user['deptNm'],
                    email=user.get('email') or None,  # 빈 문자열도 None으로 정규화
                    double_dept_name=user.get('doubleDeptNm'),
                ))
            except KeyError as e:
                # 응답 스키마 불일치 시 해당 항목만 건너뜀 — 전체 실패 방지
                logger.warning('학생 정보 파싱 실패 (필드 누락: %s) — 해당 항목 제외', e)
        return results
