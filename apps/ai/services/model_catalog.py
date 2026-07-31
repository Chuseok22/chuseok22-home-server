import logging
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache

from apps.ai.services.suh_aider_client import SuhAiderClient, SuhAiderClientError

logger = logging.getLogger(__name__)

_CACHE_KEY = 'suh_aider_model_catalog'
_CACHE_TTL_SECONDS = 1800
_MAX_WORKERS = 8
_CHAT_GROUP_LABEL = '채팅용'
_OTHER_GROUP_LABEL = '기타 (임베딩 등)'


def get_model_choices() -> list[tuple[str, list[tuple[str, str]]]]:
    """SUH-AIder에 등록된 모델을 capabilities 기준으로 그룹핑한 선택지를 반환한다.

    django.forms.ChoiceField가 그대로 받을 수 있는 [(그룹명, [(value, label), ...]), ...]
    형태다. 캐시(30분)를 우선 사용하고, 미스일 때만 SUH-AIder를 실제로 조회한다.
    """
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return cached

    client = SuhAiderClient()
    try:
        models = client.list_models()
    except SuhAiderClientError:
        logger.warning('SUH-AIder 모델 목록 조회 실패 — 빈 선택지를 반환한다.')
        return []

    chat_options: list[tuple[str, str]] = []
    other_options: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        future_to_model = {
            executor.submit(client.get_model_capabilities, model['name']): model for model in models
        }
        for future, model in future_to_model.items():
            name = model['name']
            try:
                capabilities = future.result()
            except SuhAiderClientError:
                logger.warning('SUH-AIder 모델(%s) capabilities 조회 실패 — 목록에서 제외한다.', name)
                continue

            parameter_size = model.get('details', {}).get('parameter_size', '')
            label = f'{name} ({parameter_size})' if parameter_size else name
            option = (name, label)
            if 'completion' in capabilities:
                chat_options.append(option)
            else:
                other_options.append(option)

    chat_options.sort(key=lambda option: option[0])
    other_options.sort(key=lambda option: option[0])

    choices: list[tuple[str, list[tuple[str, str]]]] = []
    if chat_options:
        choices.append((_CHAT_GROUP_LABEL, chat_options))
    if other_options:
        choices.append((_OTHER_GROUP_LABEL, other_options))

    if not choices:
        # list_models()는 성공했지만 개별 모델의 capabilities 조회가 전부 실패한 경우다.
        # 이것도 일시적 장애일 수 있으므로, list_models() 자체가 실패했을 때와 마찬가지로
        # 캐시에 저장하지 않아 다음 요청에서 재시도되게 한다.
        return choices

    cache.set(_CACHE_KEY, choices, _CACHE_TTL_SECONDS)
    return choices
