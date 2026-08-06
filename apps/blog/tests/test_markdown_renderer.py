from apps.blog.services.markdown_renderer import render_markdown


def test_render_markdown_헤딩_변환() -> None:
    result = render_markdown('# 제목\n\n본문입니다.')

    assert '<h1>제목</h1>' in result
    assert '<p>본문입니다.</p>' in result


def test_render_markdown_언어_지정_코드블록은_pygments로_하이라이팅된다() -> None:
    result = render_markdown('```python\nprint(1)\n```')

    assert 'class="codehilite"' in result
    assert 'data-lang="python"' in result
    assert '<span class="nb">print</span>' in result


def test_render_markdown_특수문자가_포함된_언어명도_인식한다() -> None:
    result = render_markdown('```c++\nint x = 1;\n```')

    assert 'data-lang="c++"' in result


def test_render_markdown_언어_미지정_코드블록은_data_lang_text로_표시된다() -> None:
    result = render_markdown('```\nplain\n```')

    assert 'data-lang="text"' in result


def test_render_markdown_crlf_줄바꿈_코드블록도_하이라이팅된다() -> None:
    """Django Admin의 textarea 제출은 줄바꿈을 \\r\\n으로 정규화한다 — 정규화 없이는
    fenced code block 추출 정규식이 매칭에 실패해 하이라이팅이 조용히 건너뛰어진다."""
    result = render_markdown('```python\r\nprint(1)\r\n```')

    assert 'data-lang="python"' in result


def test_render_markdown_crlf_줄바꿈_mermaid_블록도_인식된다() -> None:
    result = render_markdown('```mermaid\r\nflowchart LR\r\n    A --> B\r\n```')

    assert '<pre class="mermaid">flowchart LR' in result


def test_render_markdown_mermaid_블록은_다이어그램용_pre로_분리된다() -> None:
    result = render_markdown('```mermaid\nflowchart LR\n    A --> B\n```')

    assert '<pre class="mermaid">flowchart LR' in result
    assert 'A --&gt; B' in result
    assert 'codehilite' not in result


def test_render_markdown_일반_코드블록과_mermaid_블록이_섞여있어도_각각_분리된다() -> None:
    result = render_markdown('```python\nprint(1)\n```\n\n```mermaid\nflowchart LR\n    A --> B\n```')

    assert 'data-lang="python"' in result
    assert '<pre class="mermaid">flowchart LR' in result


def test_render_markdown_raw_codehilite_div가_본문에_있어도_깨지지_않는다() -> None:
    """1차 초안에서 500 에러를 냈던 케이스: 우연히 같은 클래스명의 raw HTML이 섞여 있는 경우."""
    result = render_markdown('본문\n\n<div class="codehilite">raw</div>\n\n```python\nprint(1)\n```')

    assert 'data-lang="python"' in result
    assert '<div class="codehilite">raw</div>' in result


def test_render_markdown_4개_이상_백틱_fence는_본문의_3개_백틱을_조기_종료로_보지_않는다() -> None:
    """PR 코드 리뷰에서 지적된 케이스: 4개 이상 백틱 fence 안에 예시로 3개 백틱 코드블록이
    들어 있으면, 여는 fence와 다른 길이의 백틱을 닫는 fence로 오인해 블록이 조기 종료되면
    안 된다."""
    result = render_markdown('````markdown\n예시: ```python\nprint(1)\n``` 코드블록\n````')

    assert 'data-lang="markdown"' in result
    assert '```python' in result
    assert 'print(1)' in result


def test_render_markdown_본문에_플레이스홀더와_같은_문단이_있어도_교체되지_않는다() -> None:
    """PR 코드 리뷰에서 지적된 케이스: 이전 구현은 순번 기반 플레이스홀더 키(BLOCKPLACEHOLDER0 등)를
    사용해, 본문에 우연히 같은 문자열의 단락이 있으면 그 단락까지 하이라이트 HTML로 잘못
    치환됐다. 지금은 예측 불가능한 키를 쓰므로 이런 문단은 그대로 보존돼야 한다."""
    result = render_markdown('BLOCKPLACEHOLDER0\n\n```python\nprint(1)\n```')

    assert '<p>BLOCKPLACEHOLDER0</p>' in result
    assert 'data-lang="python"' in result


def test_render_markdown_테이블_변환() -> None:
    result = render_markdown('| a | b |\n|---|---|\n| 1 | 2 |')

    assert '<table>' in result
    assert '<th>a</th>' in result


def test_render_markdown_script_태그는_제거된다() -> None:
    result = render_markdown('본문 <script>alert(1)</script> 텍스트')

    assert '<script>' not in result


def test_video_태그는_허용된_속성만_남기고_렌더링된다() -> None:
    result = render_markdown('<video controls src="/media/blog/uploads/x.mp4" onerror="alert(1)"></video>')

    assert '<video controls src="/media/blog/uploads/x.mp4">' in result
    assert 'onerror' not in result


def test_render_markdown_div_태그는_class_속성만_허용된다() -> None:
    result = render_markdown('<div class="codehilite" onclick="alert(1)">텍스트</div>')

    assert 'onclick' not in result
    assert 'class="codehilite"' in result


def test_render_markdown_빈_문자열은_빈_문자열을_반환한다() -> None:
    assert render_markdown('') == ''
