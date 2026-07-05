import markdown


def render_markdown(text: str) -> str:
    """Markdown 원문을 HTML로 변환한다."""
    return markdown.markdown(text, extensions=['fenced_code', 'tables'])
