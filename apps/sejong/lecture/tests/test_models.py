import pytest
from django.contrib import admin
from django.db import IntegrityError

from apps.sejong.lecture.models import SejongAccount


def test_sejong_account_str_returns_label() -> None:
    assert str(SejongAccount(label='친구A')) == '친구A'


@pytest.mark.django_db
def test_sejong_account_label_must_be_unique() -> None:
    SejongAccount.objects.create(label='친구A', student_id='20200001', password='pw1')

    with pytest.raises(IntegrityError):
        SejongAccount.objects.create(label='친구A', student_id='20200002', password='pw2')


def test_sejong_account_is_registered_in_admin() -> None:
    assert admin.site.is_registered(SejongAccount) is True
