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
        period_start='2026-01-01', order=101,
    )
    Career.objects.create(
        category=Career.Category.EDUCATION, organization='세종대학교', role='컴퓨터공학과',
        period_start='2022-03-01', order=100,
    )

    first = Career.objects.filter(organization__in=['추석22', '세종대학교']).order_by('order').first()

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
def test_시딩_마이그레이션으로_수상_2건이_생성되어_있다() -> None:
    awards = list(Career.objects.filter(category=Career.Category.AWARD).order_by('order'))

    assert len(awards) == 2
    assert awards[0].organization == '제4회 문화체육관광 인공지능·데이터 활용 공모전'
    assert awards[0].role == '문화데이터 우수사례 부문 장려상'
    assert awards[1].organization == '세종대학교'
    assert awards[1].role == '성적우수장학금'


@pytest.mark.django_db
def test_시딩_마이그레이션으로_활동_3건이_생성되어_있다() -> None:
    names = list(Activity.objects.order_by('order').values_list('name', flat=True))

    assert names == [
        'AROM Spring Boot 심화반 · Lead Mentor',
        'CODEGATE AI-Start-Up Hackathon',
        'Autory · 세종대 자동차제작 동아리',
    ]
