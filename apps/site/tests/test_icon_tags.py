from django.template import Context, Template
from pathlib import Path


def test_heroicons_패키지는_outline_아이콘을_inline_svg로_렌더링한다() -> None:
    template = Template('{% load heroicons %}{% heroicon_outline "eye" size=16 class="w-4 h-4" %}')

    rendered = template.render(Context({}))

    assert '<svg' in rendered
    assert 'stroke="currentColor"' in rendered


_OTHER_BRANDS_DIR = (
    Path(__file__).resolve().parent.parent.parent / 'core' / 'static' / 'core' / 'icons' / 'other-brands'
)


def test_brand_icon은_유효한_슬러그를_currentColor_svg로_렌더링한다() -> None:
    template = Template('{% load icon_tags %}{% brand_icon "github" %}')

    rendered = template.render(Context({}))

    assert '<svg' in rendered
    assert 'fill="currentColor"' in rendered
    assert 'aria-hidden="true"' in rendered
    assert '<path d="M12 .297c-6.63' in rendered


def test_brand_icon은_css_class_인자를_적용한다() -> None:
    template = Template('{% load icon_tags %}{% brand_icon "apple" css_class="w-5 h-5" %}')

    rendered = template.render(Context({}))

    assert 'class="w-5 h-5"' in rendered


def test_brand_icon은_존재하지_않는_슬러그면_빈_문자열을_반환한다() -> None:
    template = Template('{% load icon_tags %}{% brand_icon "존재하지-않는-슬러그-xyz" %}')

    rendered = template.render(Context({}))

    assert rendered == ''


def test_brand_icon은_형식에_맞는_other_brands_아이콘을_렌더링한다() -> None:
    fixture_path = _OTHER_BRANDS_DIR / 'zzz-test-conformant-brand.svg'
    fixture_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M1 2h3v4h-3z"/></svg>',
        encoding='utf-8',
    )
    try:
        template = Template('{% load icon_tags %}{% brand_icon "zzz-test-conformant-brand" %}')

        rendered = template.render(Context({}))

        assert '<path d="M1 2h3v4h-3z"/>' in rendered
    finally:
        fixture_path.unlink()


def test_brand_icon은_path가_여러_개인_비표준_svg면_빈_문자열을_반환한다() -> None:
    # other-brands README의 "24x24 단일 path" 형식을 어긴 SVG(예: devicon 원본을 그대로 복사한
    # 경우)가 들어오면, 첫 path만 잘라 억지로 렌더링하는 대신 아예 그리지 않아야 한다 — 이게 바로
    # 이번 마이그레이션이 고치려던 "깨져 보이는 아이콘"을 다시 만들지 않기 위한 방어 로직이다.
    fixture_path = _OTHER_BRANDS_DIR / 'zzz-test-nonconformant-brand.svg'
    fixture_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
        '<path d="M10 10h1z"/><path d="M20 20h1z"/></svg>',
        encoding='utf-8',
    )
    try:
        template = Template('{% load icon_tags %}{% brand_icon "zzz-test-nonconformant-brand" %}')

        rendered = template.render(Context({}))

        assert rendered == ''
    finally:
        fixture_path.unlink()
