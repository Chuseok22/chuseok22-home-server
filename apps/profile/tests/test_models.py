from django.core.exceptions import ValidationError
from django.db import connection

import pytest

from apps.profile.models import (
    Activity,
    Career,
    Certification,
    Profile,
    PullRequestHighlight,
    Skill,
    VisitorCounter,
)


@pytest.mark.django_db
def test_profile_str_representation은_이름을_반환한다() -> None:
    profile = Profile.objects.create(name='백지훈', tagline='백엔드 개발자')

    assert str(profile) == '백지훈'


@pytest.mark.django_db
def test_visitor_counter_str_representation은_누적_방문수를_보여준다() -> None:
    counter = VisitorCounter.objects.create(pk=1, count=10)

    assert str(counter) == '누적 방문 10회'


@pytest.mark.django_db
def test_skill_str_representation은_분류와_이름을_보여준다() -> None:
    skill = Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=0)

    assert str(skill) == '[Backend] Django'


@pytest.mark.django_db
def test_skill은_category_다음_order_순으로_정렬된다() -> None:
    Skill.objects.create(category=Skill.Category.FRONTEND, name='React', order=0)
    Skill.objects.create(category=Skill.Category.BACKEND, name='Django', order=1)
    Skill.objects.create(category=Skill.Category.BACKEND, name='DRF', order=0)

    names = list(Skill.objects.values_list('name', flat=True))

    assert names == ['DRF', 'Django', 'React']


@pytest.mark.django_db
def test_career_str_representation은_분류_기관_역할을_보여준다() -> None:
    career = Career.objects.create(
        category=Career.Category.EDUCATION, organization='세종대학교', role='컴퓨터공학과',
        period_start='2022-03-01', order=0,
    )

    assert str(career) == '[학력] 세종대학교 — 컴퓨터공학과'


@pytest.mark.django_db
def test_career는_order_순으로_정렬된다() -> None:
    Career.objects.create(
        category=Career.Category.WORK, organization='추석22', role='백엔드 개발자',
        period_start='2026-01-01', order=1,
    )
    Career.objects.create(
        category=Career.Category.EDUCATION, organization='세종대학교', role='컴퓨터공학과',
        period_start='2022-03-01', order=0,
    )

    first = Career.objects.first()

    assert first.organization == '세종대학교'


@pytest.mark.django_db
def test_activity_str_representation은_이름을_반환한다() -> None:
    activity = Activity.objects.create(name='동아리 스터디 운영', order=0)

    assert str(activity) == '동아리 스터디 운영'


@pytest.mark.django_db
def test_certification_str_representation은_이름과_발급기관을_보여준다() -> None:
    cert = Certification.objects.create(
        name='정보처리기사', issuer='한국산업인력공단', acquired_date='2025-01-01', order=0,
    )

    assert str(cert) == '정보처리기사 (한국산업인력공단)'


@pytest.mark.django_db
def test_certification은_credential_number와_credential_url_필드를_갖지_않는다() -> None:
    field_names = {field.name for field in Certification._meta.get_fields()}

    assert 'credential_number' not in field_names
    assert 'credential_url' not in field_names


@pytest.mark.django_db
def test_pull_request_highlight_str_representation은_저장소와_제목을_보여준다() -> None:
    pr = PullRequestHighlight.objects.create(
        title='GitHub 활동 이력 자동 정리 기능 추가', repo_name='chuseok22/chuseok22-home-server',
        pr_url='https://github.com/Chuseok22/chuseok22-home-server/pull/62', order=0,
    )

    assert str(pr) == '[chuseok22/chuseok22-home-server] GitHub 활동 이력 자동 정리 기능 추가'


@pytest.mark.django_db
def test_skill은_벤더링된_슬러그면_저장된다() -> None:
    skill = Skill(category=Skill.Category.BACKEND, name='Django', icon_slug='django', order=0)

    skill.save()

    assert Skill.objects.filter(icon_slug='django').exists()


@pytest.mark.django_db
def test_skill은_벤더링되지_않은_슬러그면_저장_시_validationerror를_발생시킨다() -> None:
    skill = Skill(category=Skill.Category.BACKEND, name='없는브랜드', icon_slug='없는-슬러그-xyz', order=0)

    with pytest.raises(ValidationError):
        skill.save()


@pytest.mark.django_db
def test_skill은_icon_slug가_비어있으면_검증을_건너뛰고_저장된다() -> None:
    skill = Skill(category=Skill.Category.ETC, name='아이콘없음', icon_slug='', order=0)

    skill.save()

    assert Skill.objects.filter(name='아이콘없음').exists()


@pytest.mark.django_db
def test_skill은_objects_create로_직접_생성해도_검증을_우회하지_못한다() -> None:
    with pytest.raises(ValidationError):
        Skill.objects.create(category=Skill.Category.BACKEND, name='없는브랜드', icon_slug='없는-슬러그-xyz', order=0)


@pytest.mark.django_db
def test_skill은_icon_slug를_바꾸지_않고_다른_필드만_수정하면_레거시_유효하지_않은_슬러그를_그대로_저장한다() -> None:
    # Skill.save()가 도입되기 "전"에 이미 저장돼 있던, 지금 기준으로는 유효하지 않은 icon_slug를
    # 가진 레코드를 흉내낸다(검증을 거치지 않고 직접 INSERT). Admin의 list_editable(order) 일괄
    # 편집처럼 icon_slug를 건드리지 않는 부분 수정이 이 레거시 데이터 때문에 막히면 안 된다.
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO profile_skill (category, name, icon_slug, "order") VALUES (%s, %s, %s, %s) RETURNING id',
            [Skill.Category.INFRA, '레거시', '존재하지-않는-레거시-슬러그', 5],
        )
        legacy_id = cursor.fetchone()[0]

    skill = Skill.objects.get(pk=legacy_id)
    skill.order = 9
    skill.save()

    skill.refresh_from_db()
    assert skill.order == 9
    assert skill.icon_slug == '존재하지-않는-레거시-슬러그'
