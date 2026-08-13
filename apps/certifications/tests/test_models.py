import pytest

from apps.certifications.models import CertificationDefinition


def test_certification_definition_기본값() -> None:
    definition = CertificationDefinition(
        name='정보처리기사',
        issuer='한국산업인력공단',
        category=CertificationDefinition.Category.NATIONAL_TECH,
        crawler_type='hrdkorea_api',
    )

    assert definition.is_active is True
    assert definition.order == 0
    assert definition.crawler_source_id == ''
    assert definition.is_always_open is False
    assert str(definition) == '정보처리기사'


@pytest.mark.django_db
def test_certification_definition_정렬은_order_다음_name_순이다() -> None:
    CertificationDefinition.objects.create(
        name='나중자격증', issuer='기관', category=CertificationDefinition.Category.ETC,
        crawler_type='manual', order=1,
    )
    CertificationDefinition.objects.create(
        name='먼저자격증', issuer='기관', category=CertificationDefinition.Category.ETC,
        crawler_type='manual', order=0,
    )

    names = list(CertificationDefinition.objects.values_list('name', flat=True))

    assert names == ['먼저자격증', '나중자격증']
