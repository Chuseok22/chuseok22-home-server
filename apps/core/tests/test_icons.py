from pathlib import Path

from apps.core.icons import is_valid_icon_slug, resolve_icon_relpath

_OTHER_BRANDS_DIR = (
    Path(__file__).resolve().parent.parent / 'static' / 'core' / 'icons' / 'other-brands'
)


def test_resolve_icon_relpath는_simple_icons에_존재하는_슬러그의_경로를_반환한다() -> None:
    relpath = resolve_icon_relpath('github')

    assert relpath == 'core/icons/simple-icons/github.svg'


def test_resolve_icon_relpath는_형식은_유효하지만_존재하지_않는_슬러그면_none을_반환한다() -> None:
    # 슬러그 형식(영문 소문자/숫자/하이픈)은 정상이지만 벤더링된 파일이 없는 경우 —
    # _VALID_SLUG_RE를 통과한 뒤 finders.find()가 실제로 못 찾는 분기를 검증한다.
    assert resolve_icon_relpath('zzz-존재하지-않는-슬러그-없음') is None
    assert resolve_icon_relpath('zzz-nonexistent-brand-slug') is None


def test_resolve_icon_relpath는_경로_순회나_비허용_문자를_포함한_슬러그를_거부한다() -> None:
    assert resolve_icon_relpath('../../../../etc/hosts') is None
    assert resolve_icon_relpath('simple-icons/github') is None  # 슬래시 포함 자체를 거부
    assert resolve_icon_relpath('한글슬러그') is None  # 정규식이 허용하지 않는 문자


def test_resolve_icon_relpath는_other_brands_세트도_확인한다() -> None:
    # other-brands는 Task 3에서 빈 디렉터리로만 스캐폴딩되므로, 실제로 그 경로가 조회되는지는
    # 테스트가 임시로 만든 픽스처 파일로 직접 검증한다(운영 데이터에는 영향 없음).
    fixture_path = _OTHER_BRANDS_DIR / 'zzz-test-fixture-brand.svg'
    fixture_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg>',
        encoding='utf-8',
    )
    try:
        assert resolve_icon_relpath('zzz-test-fixture-brand') == 'core/icons/other-brands/zzz-test-fixture-brand.svg'
    finally:
        fixture_path.unlink()


def test_is_valid_icon_slug는_존재하는_슬러그면_true다() -> None:
    assert is_valid_icon_slug('apple') is True


def test_is_valid_icon_slug는_존재하지_않는_슬러그면_false다() -> None:
    assert is_valid_icon_slug('zzz-nonexistent-brand-slug') is False


def test_other_brands_디렉터리의_모든_svg는_단일_path_형식을_따른다() -> None:
    # other-brands/README.md가 문서화한 형식 규칙(단일 <path>)을 실제 파일에 대해 검증한다.
    # 현재 디렉터리가 README.md 외에는 비어 있어 이 테스트는 오늘은 자명하게 통과하지만,
    # 향후 형식에 맞지 않는 파일이 추가되는 즉시(브랜드 아이콘 렌더링 시점이 아니라) 잡아낸다.
    import re

    path_tag_re = re.compile(r'<path\b')

    for svg_file in _OTHER_BRANDS_DIR.glob('*.svg'):
        content = svg_file.read_text(encoding='utf-8')
        path_count = len(path_tag_re.findall(content))
        assert path_count == 1, f'{svg_file.name}: expected exactly one <path>, found {path_count}'
