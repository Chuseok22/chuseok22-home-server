import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_CHAT_PATH = '/api/chat'
_TAGS_PATH = '/api/tags'
_SHOW_PATH = '/api/show'
_CONNECT_TIMEOUT = 5
_READ_TIMEOUT = 60


class SuhAiderClientError(Exception):
    """SUH-AIder 호출 실패 시 발생한다 (인증 실패, 서버 오류, 네트워크 오류, 응답 형식 이상 등)."""


class SuhAiderClient:
    """SUH-AIder AI 서버(/api/chat) 연동 클라이언트"""

    def __init__(self) -> None:
        self._base_url: str = settings.SUH_AIDER_BASE_URL
        self._api_key: str = settings.SUH_AIDER_API_KEY

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        """SUH-AIder /api/chat 호출 후 assistant 응답 텍스트(message.content)를 반환한다."""
        url = f'{self._base_url.rstrip("/")}{_CHAT_PATH}'
        headers = {'Content-Type': 'application/json', 'X-API-Key': self._api_key}
        body = {'model': model, 'messages': messages, 'stream': False}

        # HTTP 상태 코드별 의미 (docs/suh_aider_ai_server_integration_guide.md 4절 참고):
        # 401 인증 실패 / 403 권한 없음 / 404 모델 없음 / 500,502,503 서버 오류 — 모두 즉시 실패 처리, 재시도 없음
        try:
            response = requests.post(
                url, headers=headers, json=body, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT)
            )
            response.raise_for_status()
            payload = response.json()
            return payload['message']['content']
        except requests.exceptions.RequestException as exc:
            body_preview = ''
            if getattr(exc, 'response', None) is not None:
                body_preview = exc.response.text[:200]
            logger.error('SUH-AIder 호출 실패: %s | 응답 바디: %s', exc, body_preview)
            raise SuhAiderClientError(f'SUH-AIder 호출 실패: {exc}') from exc
        except (KeyError, TypeError) as exc:
            logger.error('SUH-AIder 응답 형식 이상: %s', exc)
            raise SuhAiderClientError(f'SUH-AIder 응답 형식 이상: {exc}') from exc

    def list_models(self) -> list[dict[str, object]]:
        """SUH-AIder /api/tags 호출 후 등록된 전체 모델 목록을 반환한다."""
        url = f'{self._base_url.rstrip("/")}{_TAGS_PATH}'
        headers = {'X-API-Key': self._api_key}

        try:
            response = requests.get(url, headers=headers, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
            response.raise_for_status()
            payload = response.json()
            return payload['models']
        except requests.exceptions.RequestException as exc:
            body_preview = ''
            if getattr(exc, 'response', None) is not None:
                body_preview = exc.response.text[:200]
            logger.error('SUH-AIder 모델 목록 조회 실패: %s | 응답 바디: %s', exc, body_preview)
            raise SuhAiderClientError(f'SUH-AIder 모델 목록 조회 실패: {exc}') from exc
        except (KeyError, TypeError) as exc:
            logger.error('SUH-AIder 모델 목록 응답 형식 이상: %s', exc)
            raise SuhAiderClientError(f'SUH-AIder 모델 목록 응답 형식 이상: {exc}') from exc

    def get_model_capabilities(self, model_name: str) -> list[str]:
        """SUH-AIder /api/show 호출 후 지정한 모델의 capabilities 목록을 반환한다."""
        url = f'{self._base_url.rstrip("/")}{_SHOW_PATH}'
        headers = {'Content-Type': 'application/json', 'X-API-Key': self._api_key}
        body = {'model': model_name}

        try:
            response = requests.post(
                url, headers=headers, json=body, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT)
            )
            response.raise_for_status()
            payload = response.json()
            capabilities = payload['capabilities']
            if not isinstance(capabilities, list):
                raise TypeError(f'capabilities 필드가 list 형식이 아님: {type(capabilities).__name__}')
            return capabilities
        except requests.exceptions.RequestException as exc:
            body_preview = ''
            if getattr(exc, 'response', None) is not None:
                body_preview = exc.response.text[:200]
            logger.error(
                'SUH-AIder 모델(%s) capabilities 조회 실패: %s | 응답 바디: %s', model_name, exc, body_preview
            )
            raise SuhAiderClientError(f'SUH-AIder 모델({model_name}) capabilities 조회 실패: {exc}') from exc
        except (KeyError, TypeError) as exc:
            logger.error('SUH-AIder 모델(%s) capabilities 응답 형식 이상: %s', model_name, exc)
            raise SuhAiderClientError(
                f'SUH-AIder 모델({model_name}) capabilities 응답 형식 이상: {exc}'
            ) from exc
