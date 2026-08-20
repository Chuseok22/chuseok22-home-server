import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from apps.ai.services.prompt_template import CLUB_RECRUITMENT_DETECTION_FEATURE, get_active_prompt
from apps.ai.services.suh_aider_client import SuhAiderClient, SuhAiderClientError

logger = logging.getLogger(__name__)

_MAX_HORIZON_DAYS = 400


@dataclass(frozen=True)
class RecruitmentResult:
    """LLM 판별 + grounding 검증까지 마친 결과. is_recruiting=True면 검증을 통과한 것이다."""
    is_recruiting: bool
    application_start: date | None
    application_end: date | None
    apply_url: str
    evidence_quote: str


def detect_recruitment(
    club_name: str, page_text: str, page_links: Sequence[str] = (),
) -> RecruitmentResult | None:
    """page_text에서 club_name의 모집 여부를 판별한다.

    page_links가 주어지면(비어 있지 않으면) apply_url이 실제 원문 링크 목록에 있는지까지
    grounding한다 — 비어 있으면(링크 추출 실패 등) 길이·스킴 검사만으로 완화한다.

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

    return _validate(parsed, page_text, page_links)


def _parse_json(response_text: str) -> dict | None:
    """response_text에서 첫 번째로 유효한 JSON 객체(dict)를 파싱한다.

    전체 텍스트가 그대로 JSON이면 우선 사용하고, 아니면 각 '{' 위치에서
    json.JSONDecoder.raw_decode()로 파싱을 시도한다 — 정규식으로 첫 '{'부터 마지막 '}'까지
    탐욕적으로 잡으면, 응답에 설명 텍스트나 예시 JSON이 더 섞여 있을 때 유효한 판별 결과까지
    파싱 실패로 처리되는 문제가 있어 이 방식을 쓴다. 배열·문자열 등 dict가 아닌 유효 JSON은
    실패로 취급한다 — 그렇지 않으면 이어지는 _validate의 parsed.get(...) 호출이
    AttributeError로 죽어 해당 동아리 이후 순회 전체가 중단된다."""
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(response_text):
        if char != '{':
            continue
        try:
            parsed, _end_index = decoder.raw_decode(response_text, index)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _empty_result() -> RecruitmentResult:
    return RecruitmentResult(False, None, None, '', '')


def _validate(parsed: dict, page_text: str, page_links: Sequence[str]) -> RecruitmentResult:
    """grounding·날짜 검증을 적용해 최종 RecruitmentResult를 만든다. 검증 실패 시
    is_recruiting=False로 낮춘 결과를 반환한다(판별 자체는 성공했으므로 None이 아니다)."""
    is_recruiting = parsed.get('is_recruiting') is True
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

    today = timezone.localdate()
    if end is not None and end < today:
        # 사이트가 지난 기수 공고를 그대로 노출 중인데 LLM이 이를 현재 모집으로 오판한 경우를
        # 걸러낸다 — evidence_quote는 원문에 실제로 있으므로 grounding만으로는 못 잡는다.
        logger.warning('application_end(%s)가 이미 지남(오늘: %s)', end, today)
        return _empty_result()

    if end is not None and (end - today).days > _MAX_HORIZON_DAYS:
        logger.warning('application_end(%s)가 비정상적으로 먼 미래', end)
        return _empty_result()

    apply_url = _validate_apply_url(parsed.get('apply_url'), page_links)
    return RecruitmentResult(True, start, end, apply_url, evidence_quote)


def _validate_apply_url(raw_apply_url: object, page_links: Sequence[str]) -> str:
    """apply_url을 검증한다. 형식이 잘못됐거나(길이·스킴) page_links가 주어졌는데 그 목록에
    없으면 빈 문자열로 비운다 — apply_url은 부가 정보라 이 검증 실패가 detection 전체를
    무효화하지는 않는다(호출자는 is_recruiting=True를 그대로 유지한다).

    - 길이·스킴 검사: RecruitmentDetection.apply_url이 URLField(max_length=200)라 그대로
      저장하면 DataError로 배치 전체가 중단된다.
    - page_links 검사: LLM이 원문에 없는 임의의(환각) URL을 생성해도 형식만 유효하면 통과하던
      문제를 막는다 — evidence_quote에 적용한 grounding과 같은 원리를 apply_url에도 적용한다.
      page_links가 비어 있으면(추출 실패 등) 이 검사는 생략하고 길이·스킴 검사만 적용한다.
    """
    apply_url = (raw_apply_url or '').strip()
    if not apply_url:
        return ''
    if len(apply_url) > 200 or not apply_url.lower().startswith(('http://', 'https://')):
        logger.warning('apply_url 형식이 유효하지 않아 비움: %r', apply_url[:100])
        return ''
    if page_links and apply_url not in page_links:
        logger.warning('apply_url이 원문 링크 목록에 없어 비움: %r', apply_url[:100])
        return ''
    return apply_url


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
