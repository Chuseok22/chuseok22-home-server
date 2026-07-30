import pytest
from django.core.exceptions import ValidationError

from apps.restaurants.models import RestaurantTag


@pytest.mark.django_db
def test_태그_문자열_표현은_이름이다():
    tag = RestaurantTag.objects.create(name='한식')
    assert str(tag) == '한식'


@pytest.mark.django_db
def test_대소문자만_다른_이름은_중복으로_취급된다():
    RestaurantTag.objects.create(name='Bar')
    with pytest.raises(ValidationError):
        RestaurantTag.objects.create(name='bar')
