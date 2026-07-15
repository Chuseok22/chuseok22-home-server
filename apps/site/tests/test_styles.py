from pathlib import Path

STYLES_PATH = Path(__file__).resolve().parent.parent.parent.parent / 'theme' / 'static_src' / 'src' / 'styles.css'


def test_badge_tag_파스텔_스타일이_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '.badge-tag' in content
    assert "[data-theme='dark'] .badge-tag" in content


def test_x_cloak_유틸리티가_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '[x-cloak]' in content


def test_tag_base는_태그류_공통_패딩과_폰트_크기를_정의한다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '.tag-base' in content
    assert 'padding: 0.5rem 0.9rem;' in content
    assert 'font-size: 0.8125rem;' in content


def test_tag_skill은_중립_색상_베이스를_공유한다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '.tag-skill' in content
    assert 'tag-base bg-base-200 border-base-300' in content


def test_section_box가_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '.section-box' in content
    assert 'rounded-2xl' in content


def test_stat_chip이_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '.stat-chip' in content
    assert 'badge-outline' in content


def test_htmx_indicator_유틸리티가_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '.htmx-indicator' in content
    assert '.htmx-request .htmx-indicator' in content


def test_htmx_indicator_block_유틸리티가_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '.htmx-indicator-block' in content
    assert '.htmx-request .htmx-indicator-block' in content


def test_home_page_전용_라이트_다크_토큰이_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert 'body.home-page {' in content
    assert "[data-theme='dark'] body.home-page {" in content
    assert '--home-accent: #0f9aa3;' in content
    assert '--home-accent: #35d6cf;' in content
    assert '--home-star: #f2b705;' in content
    assert '--home-star: #fbc02d;' in content


def test_home_page_prose_영역도_홈_전용_토큰_색상을_사용한다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert 'body.home-page .prose {' in content
    assert '--tw-prose-body: var(--home-ink);' in content
    assert '--tw-prose-headings: var(--home-ink);' in content
