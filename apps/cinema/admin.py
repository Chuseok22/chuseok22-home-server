from typing import Any

from django import forms
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import CinemaScreenWatchStatus, NowShowingMovie, OpenedShowDate, TrackedMovie


class YongsanImaxWatch(TrackedMovie):
    """CGV 용산아이파크몰 IMAX 감시 — Admin 화면 분리용 프록시 모델."""

    class Meta:
        proxy = True
        verbose_name = 'CGV 용산 IMAX 감시'
        verbose_name_plural = 'CGV 용산 IMAX 감시 목록'


class JamsilSuperplexWatch(TrackedMovie):
    """롯데 잠실 월드타워 수퍼플렉스 감시 — Admin 화면 분리용 프록시 모델."""

    class Meta:
        proxy = True
        verbose_name = '롯데 잠실 수퍼플렉스 감시'
        verbose_name_plural = '롯데 잠실 수퍼플렉스 감시 목록'


class _ScreenBoundTrackedMovieAdmin(admin.ModelAdmin):
    """상영관 1곳에 고정된 TrackedMovie Admin 공통 로직. cinema_screen 값은 서브클래스가
    _cinema_screen 클래스 속성으로 지정한다."""

    _cinema_screen: str = ''
    list_display = ('movie', 'is_active', 'created_at')
    list_filter = ('is_active',)
    # cinema_screen을 폼에서 완전히 제외한다 — TrackedMovie.cinema_screen은 blank=True가
    # 아니라서 제외하지 않으면 기본 ModelForm이 필수 드롭다운으로 노출하고(상영관 고정이라는
    # 화면 취지에 어긋남), save_model의 강제 대입은 폼 검증(필수값 누락)보다 늦게 실행되어
    # 애초에 저장 자체가 막힌다.
    exclude = ('cinema_screen',)

    def get_queryset(self, request: HttpRequest) -> QuerySet[TrackedMovie]:
        return super().get_queryset(request).filter(cinema_screen=self._cinema_screen)

    def formfield_for_foreignkey(
        self, db_field: Any, request: HttpRequest | None = None, **kwargs: Any,
    ) -> forms.ModelChoiceField | None:
        if db_field.name == 'movie':
            kwargs['queryset'] = NowShowingMovie.objects.filter(
                cinema_screen=self._cinema_screen, is_currently_showing=True,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(
        self, request: HttpRequest, obj: TrackedMovie | None = None, **kwargs: Any,
    ) -> type[forms.ModelForm]:
        form = super().get_form(request, obj, **kwargs)
        if obj is not None:
            # 상영 종료(is_currently_showing=False)된 영화의 감시를 수정하려 할 때, formfield_for_foreignkey가
            # 이미 상영 중인 영화로만 드롭다운을 제한해 현재 선택된 영화가 queryset에서 빠지면
            # ModelChoiceField가 invalid_choice로 저장을 막는다 — 기존 값은 항상 선택 가능하게 합친다.
            field = form.base_fields['movie']
            field.queryset = field.queryset | NowShowingMovie.objects.filter(pk=obj.movie_id)
        return form

    def save_model(
        self, request: HttpRequest, obj: TrackedMovie, form: forms.ModelForm, change: bool,
    ) -> None:
        obj.cinema_screen = self._cinema_screen
        super().save_model(request, obj, form, change)


@admin.register(YongsanImaxWatch)
class YongsanImaxWatchAdmin(_ScreenBoundTrackedMovieAdmin):
    _cinema_screen = 'cgv_yongsan_imax'


@admin.register(JamsilSuperplexWatch)
class JamsilSuperplexWatchAdmin(_ScreenBoundTrackedMovieAdmin):
    _cinema_screen = 'lotte_jamsil_superplex'


@admin.register(NowShowingMovie)
class NowShowingMovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'cinema_screen', 'is_currently_showing', 'last_seen_at')
    list_filter = ('cinema_screen', 'is_currently_showing')
    search_fields = ('title',)

    def has_add_permission(self, request: HttpRequest) -> bool:
        # sync_now_showing_movies 커맨드로만 채워지는 캐시 테이블 — 수동 생성을 막는다.
        return False


@admin.register(OpenedShowDate)
class OpenedShowDateAdmin(admin.ModelAdmin):
    list_display = ('tracked_movie', 'show_date', 'notified_at')
    list_filter = ('tracked_movie__cinema_screen',)
    readonly_fields = ('notified_at',)

    def has_add_permission(self, request: HttpRequest) -> bool:
        # 알림 발송 이력이라 수동 생성을 막는다.
        return False


@admin.register(CinemaScreenWatchStatus)
class CinemaScreenWatchStatusAdmin(admin.ModelAdmin):
    list_display = ('cinema_screen', 'consecutive_failure_count', 'alert_sent', 'updated_at')

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
