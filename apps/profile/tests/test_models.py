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
def test_pull_request_highlight_str_representation은_저장소와_제목을_보여준다() -> None:
    pr = PullRequestHighlight.objects.create(
        title='GitHub 활동 이력 자동 정리 기능 추가', repo_name='chuseok22/chuseok22-home-server',
        pr_url='https://github.com/Chuseok22/chuseok22-home-server/pull/62', order=0,
    )

    assert str(pr) == '[chuseok22/chuseok22-home-server] GitHub 활동 이력 자동 정리 기능 추가'
