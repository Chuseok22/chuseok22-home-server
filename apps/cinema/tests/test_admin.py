import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.cinema.models import NowShowingMovie, TrackedMovie


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(username='admin', email='admin@example.com', password='pw12345!')
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_용산_IMAX_감시_목록_화면은_해당_상영관_행만_보여준다(admin_client: Client) -> None:
    cgv_movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    lotte_movie = NowShowingMovie.objects.create(cinema_screen='lotte_jamsil_superplex', movie_code='B', title='B')
    TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=cgv_movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    TrackedMovie.objects.create(
        cinema_screen='lotte_jamsil_superplex', movie=lotte_movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )

    response = admin_client.get(reverse('admin:cinema_yongsanimaxwatch_changelist'))

    assert response.status_code == 200
    assert response.context['cl'].queryset.count() == 1


@pytest.mark.django_db
def test_용산_IMAX_감시_등록시_영화_드롭다운은_해당_상영관의_NowShowingMovie만_포함한다(admin_client: Client) -> None:
    NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    NowShowingMovie.objects.create(cinema_screen='lotte_jamsil_superplex', movie_code='B', title='B')

    response = admin_client.get(reverse('admin:cinema_yongsanimaxwatch_add'))

    movie_field = response.context['adminform'].form.fields['movie']
    codes = [obj.movie_code for obj in movie_field.queryset]
    assert codes == ['A']


@pytest.mark.django_db
def test_용산_IMAX_감시_등록시_cinema_screen이_자동으로_고정된다(admin_client: Client) -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    url = reverse('admin:cinema_yongsanimaxwatch_add')

    response = admin_client.post(url, {
        'movie': movie.pk, 'is_active': 'on',
        'discord_webhook_url': 'https://discord.com/api/webhooks/1/a',
    })

    assert response.status_code == 302
    tracked = TrackedMovie.objects.get(movie=movie)
    assert tracked.cinema_screen == 'cgv_yongsan_imax'


@pytest.mark.django_db
def test_잠실_수퍼플렉스_감시_목록_화면은_해당_상영관_행만_보여준다(admin_client: Client) -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='lotte_jamsil_superplex', movie_code='B', title='B')
    TrackedMovie.objects.create(
        cinema_screen='lotte_jamsil_superplex', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )

    response = admin_client.get(reverse('admin:cinema_jamsilsuperplexwatch_changelist'))

    assert response.status_code == 200
    assert response.context['cl'].queryset.count() == 1
