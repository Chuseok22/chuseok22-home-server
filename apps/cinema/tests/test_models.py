import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.cinema.models import CinemaScreenWatchStatus, NowShowingMovie, OpenedShowDate, TrackedMovie


@pytest.mark.django_db
def test_NowShowingMovie_같은_상영관_같은_movie_code는_유일해야_한다() -> None:
    NowShowingMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie_code='영화A', title='영화A',
    )
    with pytest.raises(IntegrityError):
        NowShowingMovie.objects.create(
            cinema_screen='cgv_yongsan_imax', movie_code='영화A', title='영화A(중복)',
        )


@pytest.mark.django_db
def test_TrackedMovie_생성_및_movie_FK_연결() -> None:
    movie = NowShowingMovie.objects.create(
        cinema_screen='lotte_jamsil_superplex', movie_code='24329', title='스파이더맨',
    )
    tracked = TrackedMovie.objects.create(
        cinema_screen='lotte_jamsil_superplex', movie=movie,
        discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    assert tracked.is_active is True
    assert tracked.movie.title == '스파이더맨'


@pytest.mark.django_db
def test_TrackedMovie_cinema_screen이_movie와_다르면_저장을_거부한다() -> None:
    movie = NowShowingMovie.objects.create(
        cinema_screen='lotte_jamsil_superplex', movie_code='24329', title='스파이더맨',
    )
    tracked = TrackedMovie(
        cinema_screen='cgv_yongsan_imax', movie=movie,
        discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    with pytest.raises(ValueError, match='cinema_screen'):
        tracked.save()


@pytest.mark.django_db
def test_TrackedMovie_discord_webhook_url이_discord_호스트가_아니면_검증에_실패한다() -> None:
    movie = NowShowingMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie_code='영화C', title='영화C',
    )
    tracked = TrackedMovie(
        cinema_screen='cgv_yongsan_imax', movie=movie,
        discord_webhook_url='https://evil.example.com/api/webhooks/1/a',
    )
    with pytest.raises(ValidationError):
        tracked.full_clean()


@pytest.mark.django_db
def test_OpenedShowDate_같은_감시_같은_날짜는_유일해야_한다() -> None:
    movie = NowShowingMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie_code='영화B', title='영화B',
    )
    tracked = TrackedMovie.objects.create(
        cinema_screen='cgv_yongsan_imax', movie=movie,
        discord_webhook_url='https://discord.com/api/webhooks/1/a',
    )
    OpenedShowDate.objects.create(
        tracked_movie=tracked, show_date='2026-09-05', showtimes=['10:00'],
    )
    with pytest.raises(IntegrityError):
        OpenedShowDate.objects.create(
            tracked_movie=tracked, show_date='2026-09-05', showtimes=['14:00'],
        )


@pytest.mark.django_db
def test_CinemaScreenWatchStatus_같은_상영관은_유일해야_한다() -> None:
    CinemaScreenWatchStatus.objects.create(cinema_screen='cgv_yongsan_imax')
    with pytest.raises(IntegrityError):
        CinemaScreenWatchStatus.objects.create(cinema_screen='cgv_yongsan_imax')
