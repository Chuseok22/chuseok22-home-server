import html
import re
import uuid

import bleach
import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

# 마크다운 렌더링 결과에서 허용할 태그·속성 화이트리스트.
# 본문은 사이트 소유자만 작성 가능하지만(Django Admin 또는 Ingest API), 저장된 HTML이
# 그대로 방문자에게 노출되므로 방어적으로 sanitize한다.
_ALLOWED_TAGS = [
    'p', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'em', 'del', 'code', 'pre',
    'ul', 'ol', 'li',
    'blockquote',
    'a', 'img',
    'video', 'source',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'span',
]

_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
    'video': ['src', 'controls'],
    'source': ['src', 'type'],
    'div': ['class'],
    'pre': ['class', 'data-lang'],
    'span': ['class'],
}

# 언어명 문자 집합은 python-markdown fenced_code 확장이 실제로 허용하는 [\w#.+-]와 동일하게
# 맞춘다(예: c++, c#, objective-c 같은 언어명도 인식해야 하므로 \w만으로는 부족하다).
# fence는 반드시 줄 시작(^, MULTILINE)에 오고, 여는 fence 길이(백틱 3개 이상)를 (?P=fence)로
# 그대로 되받아 닫는 fence가 최소한 그만큼은 되어야만 블록이 끝나도록 강제한다(CommonMark의
# "닫는 fence는 여는 fence 이상 길이여야 한다" 규칙과 동일) — 그래야 4개 이상 백틱으로 감싼
# 블록 안에 예시로 들어간 3개 백틱(``` ... ```)이 조기 종료를 유발하지 않는다. `*로 (?P=fence)
# 뒤에 추가 백틱을 허용해, 닫는 fence가 여는 fence보다 긴 경우도 인식한다.
_FENCED_CODE_BLOCK_PATTERN = re.compile(
    r'^(?P<fence>`{3,})(?P<lang>[\w#.+-]*)[ \t]*\n(?P<code>.*?)\n(?P=fence)`*[ \t]*$',
    re.DOTALL | re.MULTILINE,
)
_PYGMENTS_FORMATTER = HtmlFormatter(style='github-dark', cssclass='codehilite')


def _highlight_code_block(lang: str, code: str) -> str:
    """fenced code block 하나를 Pygments로 하이라이팅하고 <pre>에 data-lang 속성을 채워 넣는다."""
    label = lang or 'text'
    try:
        lexer = get_lexer_by_name(lang) if lang else TextLexer()
    except ClassNotFound:
        lexer = TextLexer()
    highlighted = highlight(code, lexer, _PYGMENTS_FORMATTER)
    return highlighted.replace('<pre>', f'<pre data-lang="{label}">', 1)


def render_markdown(text: str) -> str:
    """Markdown 원문을 HTML로 변환한 뒤 허용된 태그·속성만 남기고 sanitize한다.

    fenced code block(``` ... ```)은 markdown.markdown() 호출 전에 모두 직접 추출해
    플레이스홀더로 치환한다. mermaid 블록은 Pygments가 렉서를 지원하지 않으므로 원본
    텍스트를 그대로 보존하고, 나머지는 Pygments로 직접 하이라이팅해 <pre>에 data-lang
    속성을 채워 넣는다(코드블록 헤더 JS가 이 속성으로 언어 라벨을 표시한다). 이렇게 모든
    fenced block을 렌더링 전에 미리 처리해두면, 렌더링 결과에서 위치 기반으로 다시 찾아
    매칭할 필요가 없어 순서 불일치로 인한 오류(예: 본문에 우연히 같은 클래스명의 raw HTML이
    섞여 있는 경우) 걱정 없이 안전하게 대응할 수 있다.
    """
    # python-markdown은 markdown.markdown() 내부에서 CRLF를 자동 정규화하지만, 이 함수의
    # fenced code block 추출은 그보다 먼저 실행되므로 별도로 정규화해야 한다. Django Admin의
    # <textarea> 제출은 줄바꿈을 \r\n으로 정규화하므로, 정규화하지 않으면 정규식의 \n 매칭이
    # 실패해 코드블록 하이라이팅이 조용히 건너뛰어진다.
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    placeholders: dict[str, str] = {}

    def _extract_fenced_block(match: re.Match[str]) -> str:
        lang = match.group('lang')
        code = match.group('code')
        # 순번 기반 키(BLOCKPLACEHOLDER0 등)는 본문에 우연히 같은 문자열이 단락으로 존재하면
        # 그 단락까지 하이라이트 HTML로 치환해버릴 수 있어, 예측 불가능한 토큰을 사용한다.
        key = f'BLOCKPLACEHOLDER{uuid.uuid4().hex}'
        if lang == 'mermaid':
            placeholders[key] = f'<pre class="mermaid">{html.escape(code)}</pre>'
        else:
            placeholders[key] = _highlight_code_block(lang, code)
        return f'\n\n{key}\n\n'

    processed_text = _FENCED_CODE_BLOCK_PATTERN.sub(_extract_fenced_block, text)
    rendered_html = markdown.markdown(processed_text, extensions=['fenced_code', 'tables'])
    for key, block_html in placeholders.items():
        rendered_html = rendered_html.replace(f'<p>{key}</p>', block_html)

    return bleach.clean(rendered_html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES, strip=True)
