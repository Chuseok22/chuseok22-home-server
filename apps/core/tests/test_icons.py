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
