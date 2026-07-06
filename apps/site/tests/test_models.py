import pytest
from django.core.exceptions import ValidationError

from apps.site.models import Tool


def test_reverse_가능한_url_name은_통과한다() -> None:
    tool = Tool(
        title='스터디룸 예약', slug='clean-test-valid', description='설명',
        url_name='site:lab-library',
    )

    tool.clean()


def test_reverse_불가능한_url_name은_ValidationError() -> None:
    tool = Tool(
        title='잘못된 도구', slug='clean-test-invalid', description='설명',
        url_name='site:does-not-exist',
    )

    with pytest.raises(ValidationError):
        tool.clean()
