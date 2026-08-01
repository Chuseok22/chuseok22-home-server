import logging
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

import requests
from django.utils import timezone

from apps.places.models import Place, PlaceSyncFolder

logger = logging.getLogger(__name__)

_FAVORITE_LIST_URL = 'https://map.kakao.com/favorite/list'
_REFERER = 'https://map.kakao.com/'
_CONNECT_TIMEOUT = 5
_READ_TIMEOUT = 10
# 폴더당 최대 페이지 수 안전장치 — 카카오 응답이 next_id를 계속 새로 발급해도 무한 루프에
# 빠지지 않도록 상한을 둔다. 현재 최대 폴더(맛집, 556건)도 페이지당 500건 기준 2페이지면 충분하다.
_MAX_PAGES = 50
# resolve_folder_id()가 요청을 허용하는 호스트 — 스태프 폼 입력을 그대로 requests.get에
# 넘기므로, 내부망/클라우드 메타데이터 주소 등으로의 SSRF를 막기 위해 카카오 도메인만 허용한다.
_ALLOWED_SHARE_LINK_HOSTS = {'kko.to', 'map.kakao.com'}


class KakaoFavoriteSyncError(Exception):
    """카카오맵 즐겨찾기 폴더 조회/공유 링크 해석 실패 시 발생한다
    (네트워크 오류, 비2xx 응답, 응답 형식 이상 등)."""


@dataclass(frozen=True)
class ChangedPlace:
    """카카오맵에서 item_updated_at이 바뀐 것으로 감지된 기존 장소.
    이름/주소 등 필드는 자동으로 덮어쓰지 않고, 관리자에게 알림으로만 전달해 직접 확인하게 한다."""

    name: str
    kakao_place_url: str


@dataclass(frozen=True)
class SyncResult:
    """한 폴더 동기화 결과."""

    created_count: int
    skipped_count: int
    changed_places: list[ChangedPlace]
    # 장소가 아닌 북마크(주소 즐겨찾기 등)이거나 형식이 이상해 건너뛴 항목 수
    malformed_count: int = 0


def resolve_folder_id(value: str) -> str:
    """PlaceSyncFolder.kakao_folder_id 입력값을 정규화한다.
    카카오맵 폴더 공유 링크(예: https://kko.to/XXXXXXXXXX)를 그대로 붙여넣은 경우 리다이렉트를
    따라가 실제 folderid를 추출하고, 이미 숫자 ID 문자열이면 그대로 반환한다."""
    if not value.startswith('http'):
        return value

    hostname = urlsplit(value).hostname
    if hostname not in _ALLOWED_SHARE_LINK_HOSTS:
        raise KakaoFavoriteSyncError(f'허용되지 않은 호스트입니다: {hostname}')

    try:
        response = requests.get(
            value, headers={'Referer': _REFERER}, allow_redirects=True,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error('카카오맵 폴더 공유 링크 해석 실패: %s', exc)
        raise KakaoFavoriteSyncError(f'카카오맵 폴더 공유 링크 해석 실패: {exc}') from exc

    folder_ids = parse_qs(urlsplit(response.url).query).get('folderid')
    if not folder_ids:
        raise KakaoFavoriteSyncError(f'공유 링크에서 folderid를 찾을 수 없습니다: {response.url}')
    return folder_ids[0]


def _fetch_favorites_page(folder_id: str, next_id: int | None) -> dict:
    params: dict[str, str | int] = {'folderid': folder_id}
    if next_id is not None:
        params['next_id'] = next_id

    try:
        response = requests.get(
            _FAVORITE_LIST_URL, headers={'Referer': _REFERER}, params=params,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        logger.error('카카오맵 즐겨찾기 조회 실패 (folder_id=%s): %s', folder_id, exc)
        raise KakaoFavoriteSyncError(f'카카오맵 즐겨찾기 조회 실패: {exc}') from exc
    except ValueError as exc:
        logger.error('카카오맵 즐겨찾기 응답이 JSON이 아닙니다 (folder_id=%s): %s', folder_id, exc)
        raise KakaoFavoriteSyncError(f'카카오맵 즐겨찾기 응답이 JSON이 아닙니다: {exc}') from exc

    if not isinstance(payload.get('favorites'), list):
        logger.error('카카오맵 즐겨찾기 응답 형식 이상 (folder_id=%s): favorites 키 없음/타입 이상', folder_id)
        raise KakaoFavoriteSyncError(f'카카오맵 즐겨찾기 응답 형식 이상: favorites 키 없음 (folder_id={folder_id})')
    return payload


def sync_folder(folder: PlaceSyncFolder) -> SyncResult:
    """폴더 안의 즐겨찾기를 next_id로 전부 페이지네이션 조회한다.
    아직 없는 장소는 Place로 새로 생성하고, 이미 있는 장소는 item_updated_at이 마지막 동기화
    때와 다르면 변경된 것으로만 표시한다(이름/주소 등은 자동으로 덮어쓰지 않음 — 폐업인지 단순
    정보 수정인지 카카오 API로는 구분할 수 없어 관리자가 직접 확인해야 한다). kakao_item_updated_at이
    비어있는(=아직 추적을 시작하지 않은, 예: 수동 등록) 기존 장소는 알림 없이 기준값만 채운다.
    즐겨찾기에서 빠진 장소를 감지해 삭제하는 기능은 의도적으로 두지 않는다 — 개인 평점/한줄평 등
    큐레이션 데이터가 유실될 수 있어, 삭제는 항상 어드민에서 수동으로 한다.
    장소가 아닌 북마크(주소 즐겨찾기 등)나 형식이 이상한 개별 항목은 폴더 전체를 중단시키지 않고
    건너뛰며 malformed_count로만 집계한다."""
    created_count = 0
    skipped_count = 0
    malformed_count = 0
    changed_places: list[ChangedPlace] = []
    next_id: int | None = None
    seen_next_ids: set[int] = set()

    for _ in range(_MAX_PAGES):
        payload = _fetch_favorites_page(folder.kakao_folder_id, next_id)
        favorites = payload['favorites']

        for item in favorites:
            if item.get('type') != 'PLACE':
                # 주소 즐겨찾기 등 장소가 아닌 북마크는 건너뛴다.
                malformed_count += 1
                continue
            try:
                kakao_place_id = str(item['key'])
                display_name = item['display1']
                latitude = round(item['lat'], 7)
                longitude = round(item['lon'], 7)
            except (KeyError, TypeError) as exc:
                # 항목 하나의 형식 이상으로 폴더 전체 동기화가 영구히 멈추면 안 된다
                # (매주 같은 지점에서 계속 실패해 last_synced_at이 다시는 갱신되지 않음) —
                # 이 항목만 건너뛰고 계속 진행한다.
                logger.warning(
                    '카카오맵 즐겨찾기 항목 형식 이상, 건너뜀 (folder_id=%s): %s',
                    folder.kakao_folder_id, exc,
                )
                malformed_count += 1
                continue

            item_updated_at = item.get('item_updated_at', '')
            existing = Place.objects.filter(kakao_place_id=kakao_place_id).first()

            if existing is None:
                Place.objects.create(
                    name=display_name,
                    address=item.get('display2', ''),
                    latitude=latitude,
                    longitude=longitude,
                    kakao_place_id=kakao_place_id,
                    kakao_place_url=f'https://place.map.kakao.com/{kakao_place_id}',
                    kakao_item_updated_at=item_updated_at,
                    note=item.get('memo', ''),
                    category=folder.category,
                )
                created_count += 1
                continue

            skipped_count += 1
            if not existing.kakao_item_updated_at:
                # 아직 추적 시작 전(수동 등록 등)이면 알림 없이 기준값만 채운다.
                if item_updated_at:
                    existing.kakao_item_updated_at = item_updated_at
                    existing.save(update_fields=['kakao_item_updated_at'])
            elif item_updated_at and existing.kakao_item_updated_at != item_updated_at:
                changed_places.append(
                    ChangedPlace(name=existing.name, kakao_place_url=existing.kakao_place_url),
                )
                # 다음 동기화 때 같은 변경을 다시 알리지 않도록 추적용 값만 갱신한다.
                existing.kakao_item_updated_at = item_updated_at
                existing.save(update_fields=['kakao_item_updated_at'])

        next_id = payload.get('next_id')
        if not favorites or not next_id or next_id in seen_next_ids:
            break
        seen_next_ids.add(next_id)
    else:
        logger.error(
            '폴더 동기화가 최대 페이지 수(%d)에 도달했습니다 (folder_id=%s) — 동기화가 중단됐을 수 있습니다.',
            _MAX_PAGES, folder.kakao_folder_id,
        )

    folder.last_synced_at = timezone.now()
    folder.save(update_fields=['last_synced_at'])
    return SyncResult(
        created_count=created_count, skipped_count=skipped_count,
        changed_places=changed_places, malformed_count=malformed_count,
    )
