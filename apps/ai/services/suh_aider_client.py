import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_CHAT_PATH = '/api/chat'
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

        response = requests.post(url, headers=headers, json=body, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        response.raise_for_status()
        payload = response.json()
        return payload['message']['content']
