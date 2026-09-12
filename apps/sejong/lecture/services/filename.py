import re

_FORBIDDEN_CHARS_RE = re.compile(r'[/\\:*?"<>|\s]+')
# job.id·구분자·확장자를 제외한 "이름 부분"(course_name+lecture_title)의 바이트 예산.
_NAME_PART_BYTE_BUDGET = 200
# course_name이 lecture_title에 밀려 완전히 안 보이지 않도록 최소한 보장하는 바이트 수.
_MIN_COURSE_NAME_BYTES = 20


def build_lecture_filename(course_name: str, lecture_title: str, job_id: int | None = None) -> str:
    """course_name/lecture_title을 sanitize하고 길이 예산에 맞춰 잘라 mp4 파일명을 만든다.

    job_id가 주어지면 NAS 저장용(`{course}_{lecture}_{id}.mp4`), 없으면 브라우저
    다운로드용(`{course}_{lecture}.mp4`)이다. lecture_title을 우선 보존하고, course_name은
    최소 `_MIN_COURSE_NAME_BYTES`바이트를 보장한 채로 남는 예산만큼만 담는다.
    """
    sanitized_course = _sanitize(course_name)
    sanitized_lecture = _sanitize(lecture_title)

    max_lecture_bytes = _NAME_PART_BYTE_BUDGET - _MIN_COURSE_NAME_BYTES
    truncated_lecture = _truncate_utf8(sanitized_lecture, max_lecture_bytes)

    max_course_bytes = _NAME_PART_BYTE_BUDGET - len(truncated_lecture.encode('utf-8'))
    truncated_course = _truncate_utf8(sanitized_course, max_course_bytes)

    name = f'{truncated_course}_{truncated_lecture}'
    if job_id is not None:
        name = f'{name}_{job_id}'
    return f'{name}.mp4'


def _sanitize(text: str) -> str:
    """파일시스템 금지문자(`/ \\ : * ? " < > |`)와 공백을 전부 `_`로 치환한다.

    Windows/SMB로 NAS 볼륨을 열어볼 가능성을 감안해 POSIX에서만 문제되는 `/` 외에
    Windows 금지문자까지 전부 치환한다. 연속된 금지문자/공백은 언더스코어 하나로 묶어
    `___` 같은 반복을 피한다.
    """
    return _FORBIDDEN_CHARS_RE.sub('_', text)


def _truncate_utf8(text: str, max_bytes: int) -> str:
    """UTF-8 인코딩 기준 max_bytes를 넘지 않도록, 멀티바이트 문자 중간에서 끊지 않고 자른다."""
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes]
    while truncated:
        try:
            return truncated.decode('utf-8')
        except UnicodeDecodeError:
            truncated = truncated[:-1]
    return ''
