import bleach
import markdown

# 마크다운 렌더링 결과에서 허용할 태그·속성 화이트리스트.
# 본문은 본인(owner)만 작성 가능하지만, 저장된 HTML이 그대로 방문자에게 노출되므로 방어적으로 sanitize한다.
_ALLOWED_TAGS = [
    'p', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'em', 'del', 'code', 'pre',
    'ul', 'ol', 'li',
    'blockquote',
    'a', 'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
]

_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
}


def render_markdown(text: str) -> str:
    """Markdown 원문을 HTML로 변환한 뒤 허용된 태그·속성만 남기고 sanitize한다."""
    html = markdown.markdown(text, extensions=['fenced_code', 'tables'])
    return bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES, strip=True)
