import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.cinema.models import NowShowingMovie, TrackedMovie


@pytest.fixture
def admin_client(db) -> Client:
    user = User.objects.create_superuser(  # noqa: S106 - force_login()만 쓰므로 실제 인증에 사용되지 않는 테스트 전용 값
        username='admin', email='admin@example.com', password='pw12345!',
    )
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
    NowShowingMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie_code='C', title='C', is_currently_showing=False,
    )

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
def test_상영_종료된_영화의_감시_수정_화면_저장은_성공한다(admin_client: Client) -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    tracked = TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    # sync_now_showing_movies가 상영 종료된 영화를 삭제하지 않고 플래그만 내리는 상황을 재현한다 —
    # formfield_for_foreignkey가 is_currently_showing=True로만 드롭다운을 제한하면, 이 시점에
    # 이미 선택된 movie가 queryset에서 빠져 ModelChoiceField가 invalid_choice로 저장을 막는다.
    movie.is_currently_showing = False
    movie.save()
    url = reverse('admin:cinema_yongsanimaxwatch_change', args=[tracked.pk])

    response = admin_client.post(url, {
        'movie': movie.pk, 'is_active': '',
        'discord_webhook_url': 'https://discord.com/api/webhooks/1/a',
    })

    assert response.status_code == 302
    tracked.refresh_from_db()
    assert tracked.is_active is False
    assert tracked.movie_id == movie.pk


@pytest.mark.django_db
def test_NowShowingMovie_캐시는_수정_화면_저장을_거부한다(admin_client: Client) -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    url = reverse('admin:cinema_nowshowingmovie_change', args=[movie.pk])

    response = admin_client.post(url, {'cinema_screen': 'lotte_jamsil_superplex', 'movie_code': 'A', 'title': 'A'})

    assert response.status_code == 403
    movie.refresh_from_db()
    assert movie.cinema_screen == 'cgv_yongsan_imax'


@pytest.mark.django_db
def test_NowShowingMovie_캐시는_삭제를_거부한다(admin_client: Client) -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='cgv_yongsan_imax', movie_code='A', title='A')
    url = reverse('admin:cinema_nowshowingmovie_delete', args=[movie.pk])

    response = admin_client.post(url, {'post': 'yes'})

    assert response.status_code == 403
    assert NowShowingMovie.objects.filter(pk=movie.pk).exists()


@pytest.mark.django_db
def test_잠실_수퍼플렉스_감시_목록_화면은_해당_상영관_행만_보여준다(admin_client: Client) -> None:
    movie = NowShowingMovie.objects.create(cinema_screen='lotte_jamsil_superplex', movie_code='B', title='B')
    TrackedMovie.objects.create(
        cinema_screen='lotte_jamsil_superplex', movie=movie, discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )

    response = admin_client.get(reverse('admin:cinema_jamsilsuperplexwatch_changelist'))

    assert response.status_code == 200
    assert response.context['cl'].queryset.count() == 1
