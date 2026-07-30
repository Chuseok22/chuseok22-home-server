import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_SEARCH_URL = 'https://dapi.kakao.com/v2/local/search/keyword.json'
_CONNECT_TIMEOUT = 5
_READ_TIMEOUT = 10


class KakaoApiError(Exception):
    """카카오 로컬 API 호출 실패 시 발생한다 (인증 실패, 서버 오류, 네트워크 오류, 응답 형식 이상 등)."""


@dataclass(frozen=True)
class KakaoPlaceResult:
    """카카오 로컬 API 키워드 검색 결과 한 건."""

    name: str
    address: str
    road_address: str
    latitude: float
    longitude: float
    category: str
    place_url: str


def search_places(query: str) -> list[KakaoPlaceResult]:
    """카카오 로컬 REST API 키워드 검색으로 장소 목록을 조회한다."""
    headers = {'Authorization': f'KakaoAK {settings.KAKAO_REST_API_KEY}'}
    params = {'query': query}

    try:
        response = requests.get(
            _SEARCH_URL, headers=headers, params=params, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
        response.raise_for_status()
        documents = response.json()['documents']
        return [
            KakaoPlaceResult(
                name=doc['place_name'],
                address=doc['address_name'],
                road_address=doc['road_address_name'],
                # Restaurant.latitude/longitude가 DecimalField(decimal_places=7)이므로,
                # 카카오가 그 이상의 정밀도를 반환해도 Admin 저장 시 검증에 걸리지 않도록
                # 여기서 미리 반올림해둔다.
                latitude=round(float(doc['y']), 7),
                longitude=round(float(doc['x']), 7),
                category=doc['category_name'],
                place_url=doc['place_url'],
            )
            for doc in documents
        ]
    except requests.exceptions.RequestException as exc:
        body_preview = exc.response.text[:200] if getattr(exc, 'response', None) is not None else ''
        logger.error('카카오 로컬 API 호출 실패: %s | 응답 바디: %s', exc, body_preview)
        raise KakaoApiError(f'카카오 로컬 API 호출 실패: {exc}') from exc
    except (KeyError, TypeError, ValueError) as exc:
        logger.error('카카오 로컬 API 응답 형식 이상: %s', exc)
        raise KakaoApiError(f'카카오 로컬 API 응답 형식 이상: {exc}') from exc
