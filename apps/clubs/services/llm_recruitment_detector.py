import json
import logging
import re
from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from apps.ai.services.prompt_template import CLUB_RECRUITMENT_DETECTION_FEATURE, get_active_prompt
from apps.ai.services.suh_aider_client import SuhAiderClient, SuhAiderClientError

logger = logging.getLogger(__name__)

_MAX_HORIZON_DAYS = 400
_JSON_BLOCK_PATTERN = re.compile(r'\{.*\}', re.DOTALL)


@dataclass(frozen=True)
class RecruitmentResult:
    """LLM 판별 + grounding 검증까지 마친 결과. is_recruiting=True면 검증을 통과한 것이다."""
    is_recruiting: bool
    application_start: date | None
    application_end: date | None
    apply_url: str
    evidence_quote: str


def detect_recruitment(club_name: str, page_text: str) -> RecruitmentResult | None:
    """page_text에서 club_name의 모집 여부를 판별한다.

    반환값이 None이면 판별 자체가 실패한 것이다(프롬프트 미설정, LLM 호출 실패, 응답 파싱 완전
    실패) — 호출자는 이를 실패로 카운트해야 한다. None이 아니면 기술적으로는 성공한 것이며,
    is_recruiting은 grounding·날짜 검증까지 통과한 최종 판단이다(오탐 방지를 위해 검증 실패 시
    이 함수 내부에서 이미 False로 낮춘다).
    """
    prompt = get_active_prompt(CLUB_RECRUITMENT_DETECTION_FEATURE)
    if prompt is None:
        logger.error('CLUB_RECRUITMENT_DETECTION 활성 프롬프트가 없음')
        return None

    messages = [
        {'role': 'system', 'content': prompt.system_prompt},
        {'role': 'user', 'content': f'동아리명: {club_name}\n\n[본문]\n{page_text}'},
    ]
    try:
        response_text = SuhAiderClient().chat(model=prompt.model, messages=messages)
    except SuhAiderClientError as e:
        logger.error('SUH-AIder 호출 실패 (club=%s): %s', club_name, e)
        return None

    parsed = _parse_json(response_text)
    if parsed is None:
        logger.error('LLM 응답 JSON 파싱 실패 (club=%s): %s', club_name, response_text[:200])
        return None

    return _validate(parsed, page_text)


def _parse_json(response_text: str) -> dict | None:
    """response_text에서 JSON 객체(dict)를 파싱한다. 배열·문자열·숫자 등 dict가 아닌 유효
    JSON이 파싱되는 경우도 실패로 취급한다 — 그렇지 않으면 이어지는 _validate의
    parsed.get(...) 호출이 AttributeError로 죽어 해당 동아리 이후 순회 전체가 중단된다."""
    for candidate in (response_text, _extract_json_block(response_text)):
        if candidate is None:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_json_block(response_text: str) -> str | None:
    match = _JSON_BLOCK_PATTERN.search(response_text)
    return match.group(0) if match else None


def _empty_result() -> RecruitmentResult:
    return RecruitmentResult(False, None, None, '', '')


def _validate(parsed: dict, page_text: str) -> RecruitmentResult:
    """grounding·날짜 검증을 적용해 최종 RecruitmentResult를 만든다. 검증 실패 시
    is_recruiting=False로 낮춘 결과를 반환한다(판별 자체는 성공했으므로 None이 아니다)."""
    is_recruiting = bool(parsed.get('is_recruiting'))
    if not is_recruiting:
        return _empty_result()

    evidence_quote = (parsed.get('evidence_quote') or '').strip()
    if not evidence_quote or evidence_quote not in page_text:
        logger.warning('grounding 검증 실패 — evidence_quote가 원문에 없음: %r', evidence_quote[:100])
        return _empty_result()

    start = _parse_date(parsed.get('application_start'))
    if parsed.get('application_start') and start is None:
        logger.warning('application_start 날짜 파싱 실패: %r', parsed.get('application_start'))
        return _empty_result()

    end = _parse_date(parsed.get('application_end'))
    if parsed.get('application_end') and end is None:
        logger.warning('application_end 날짜 파싱 실패: %r', parsed.get('application_end'))
        return _empty_result()

    if start is not None and end is not None and start > end:
        logger.warning('application_start(%s) > application_end(%s)', start, end)
        return _empty_result()

    if end is not None and (end - timezone.localdate()).days > _MAX_HORIZON_DAYS:
        logger.warning('application_end(%s)가 비정상적으로 먼 미래', end)
        return _empty_result()

    apply_url = (parsed.get('apply_url') or '').strip()
    return RecruitmentResult(True, start, end, apply_url, evidence_quote)


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
