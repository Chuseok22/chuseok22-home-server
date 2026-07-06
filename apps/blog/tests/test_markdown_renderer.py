from apps.blog.services.markdown_renderer import render_markdown


def test_render_markdown_헤딩_변환() -> None:
    result = render_markdown('# 제목\n\n본문입니다.')

    assert '<h1>제목</h1>' in result
    assert '<p>본문입니다.</p>' in result


def test_render_markdown_코드_블록_변환() -> None:
    result = render_markdown('```python\nprint(1)\n```')

    assert '<pre><code>print(1)' in result


def test_render_markdown_테이블_변환() -> None:
    result = render_markdown('| a | b |\n|---|---|\n| 1 | 2 |')

    assert '<table>' in result
    assert '<th>a</th>' in result


def test_render_markdown_script_태그는_제거된다() -> None:
    result = render_markdown('본문 <script>alert(1)</script> 텍스트')

    assert '<script>' not in result
