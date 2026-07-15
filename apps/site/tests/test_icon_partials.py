from django.template.loader import render_to_string


def test_eye_아이콘_partial은_svg를_렌더링한다() -> None:
    html = render_to_string('site/partials/icons/eye.svg.html')

    assert '<svg' in html
    assert 'viewBox="0 0 24 24"' in html
    assert 'stroke="currentColor"' in html
