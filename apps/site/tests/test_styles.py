from pathlib import Path

STYLES_PATH = Path(__file__).resolve().parent.parent.parent.parent / 'theme' / 'static_src' / 'src' / 'styles.css'


def test_badge_tag_파스텔_스타일이_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '.badge-tag' in content
    assert "[data-theme='dark'] .badge-tag" in content


def test_x_cloak_유틸리티가_정의되어_있다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert '[x-cloak]' in content


def test_badge_tag는_배지_높이는_유지하고_글자_크기만_줄인다() -> None:
    content = STYLES_PATH.read_text(encoding='utf-8')

    assert 'badge-lg' in content
    assert 'font-size: 0.75rem;' in content
