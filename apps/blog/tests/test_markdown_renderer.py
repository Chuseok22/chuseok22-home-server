from apps.blog.services.markdown_renderer import render_markdown


def test_render_markdown_헤딩_변환() -> None:
    result = render_markdown('# 제목\n\n본문입니다.')

    assert '<h1>제목</h1>' in result
    assert '<p>본문입니다.</p>' in result
