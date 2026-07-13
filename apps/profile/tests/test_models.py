import pytest

from apps.profile.models import Profile, VisitorCounter


@pytest.mark.django_db
def test_profile_str_representation은_이름을_반환한다() -> None:
    profile = Profile.objects.create(name='백지훈', tagline='백엔드 개발자')

    assert str(profile) == '백지훈'


@pytest.mark.django_db
def test_visitor_counter_str_representation은_누적_방문수를_보여준다() -> None:
    counter = VisitorCounter.objects.create(pk=1, count=10)

    assert str(counter) == '누적 방문 10회'
