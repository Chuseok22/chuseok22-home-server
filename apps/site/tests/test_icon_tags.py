from django.template import Context, Template


def test_heroicons_패키지는_outline_아이콘을_inline_svg로_렌더링한다() -> None:
    template = Template('{% load heroicons %}{% heroicon_outline "eye" size=16 class="w-4 h-4" %}')

    rendered = template.render(Context({}))

    assert '<svg' in rendered
    assert 'stroke="currentColor"' in rendered
