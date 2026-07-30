from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class RestaurantTag(models.Model):
    """맛집 태그. 대소문자만 다른 동일 태그의 중복 생성을 막는다 (apps.blog.Tag와 동일한 패턴)."""

    name = models.CharField(max_length=50, verbose_name='이름')
    slug = models.SlugField(unique=True, blank=True, verbose_name='슬러그')

    class Meta:
        db_table = 'restaurants_restaurant_tag'
        ordering = ['name']
        verbose_name = '맛집 태그'
        verbose_name_plural = '맛집 태그 목록'
        constraints = [
            models.UniqueConstraint(Lower('name'), name='unique_restaurant_tag_name_ci'),
        ]

    def clean(self) -> None:
        if RestaurantTag.objects.filter(name__iexact=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(f"태그 '{self.name}'이 이미 존재합니다 (대소문자 무시).")

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Restaurant(models.Model):
    """카카오 로컬 API 검색으로 등록하는 맛집. 좌표는 지도 마커 및 2단계 위치 검색에 사용한다."""

    class MealTime(models.TextChoices):
        BREAKFAST = 'breakfast', '아침'
        LUNCH = 'lunch', '점심'
        DINNER = 'dinner', '저녁'
        ALL_DAY = 'all_day', '상시'

    name = models.CharField(max_length=100, verbose_name='상호명')
    address = models.CharField(max_length=255, blank=True, verbose_name='지번 주소')
    road_address = models.CharField(max_length=255, blank=True, verbose_name='도로명 주소')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='위도')
    longitude = models.DecimalField(max_digits=10, decimal_places=7, verbose_name='경도')
    kakao_place_url = models.URLField(blank=True, verbose_name='카카오맵 링크')
    category = models.CharField(max_length=100, blank=True, verbose_name='카카오 카테고리')
    tags = models.ManyToManyField(RestaurantTag, blank=True, related_name='restaurants', verbose_name='태그')
    meal_time = models.CharField(
        max_length=20, choices=MealTime.choices, default=MealTime.ALL_DAY, verbose_name='식사 시간대',
    )
    personal_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='개인 평점',
    )
    personal_review = models.CharField(max_length=200, blank=True, verbose_name='한줄 평')
    note = models.TextField(blank=True, verbose_name='비고')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'restaurants_restaurant'
        ordering = ['-created_at']
        verbose_name = '맛집'
        verbose_name_plural = '맛집 목록'

    def __str__(self) -> str:
        return self.name


class RestaurantSuggestion(models.Model):
    """방문자가 새 맛집을 제보하는 검토 대기 큐. Restaurant 본체와 분리해 상태 머신을 두지 않는다."""

    restaurant_name = models.CharField(max_length=100, verbose_name='제보 상호명')
    kakao_place_url = models.URLField(blank=True, verbose_name='카카오맵 링크')
    message = models.TextField(blank=True, verbose_name='추천 이유')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='restaurant_suggestions', verbose_name='제보자',
    )
    is_reviewed = models.BooleanField(default=False, verbose_name='검토 완료')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'restaurants_restaurant_suggestion'
        ordering = ['-created_at']
        verbose_name = '맛집 제보'
        verbose_name_plural = '맛집 제보 목록'

    def __str__(self) -> str:
        return f'{self.restaurant_name} ({self.submitted_by})'
