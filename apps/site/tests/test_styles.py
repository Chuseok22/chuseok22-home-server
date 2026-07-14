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
