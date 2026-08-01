from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class PlaceTag(models.Model):
    """장소 태그. 대소문자만 다른 동일 태그의 중복 생성을 막는다."""

    name = models.CharField(max_length=50, verbose_name='이름')
    slug = models.SlugField(unique=True, blank=True, verbose_name='슬러그')

    class Meta:
        db_table = 'places_place_tag'
        ordering = ['name']
        verbose_name = '장소 태그'
        verbose_name_plural = '장소 태그 목록'
        constraints = [
            models.UniqueConstraint(Lower('name'), name='unique_place_tag_name_ci'),
        ]

    def clean(self) -> None:
        if PlaceTag.objects.filter(name__iexact=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(f"태그 '{self.name}'이 이미 존재합니다 (대소문자 무시).")

    def save(self, *args: object, **kwargs: object) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Place(models.Model):
    """카카오 로컬 API 검색 또는 카카오맵 즐겨찾기 동기화로 등록하는 장소."""

    class Category(models.TextChoices):
        RESTAURANT = 'restaurant', '맛집'
        CAFE = 'cafe', '카페'
        BAR = 'bar', '바'
        DATE_COURSE = 'date_course', '데이트코스'
        ACCOMMODATION = 'accommodation', '숙소'

    class MealTime(models.TextChoices):
        BREAKFAST = 'breakfast', '아침'
        LUNCH = 'lunch', '점심'
        DINNER = 'dinner', '저녁'
        ALL_DAY = 'all_day', '상시'

    name = models.CharField(max_length=100, verbose_name='상호명')
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.RESTAURANT, verbose_name='카테고리',
    )
    address = models.CharField(max_length=255, blank=True, verbose_name='지번 주소')
    road_address = models.CharField(max_length=255, blank=True, verbose_name='도로명 주소')
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7,
        validators=[MinValueValidator(Decimal('-90')), MaxValueValidator(Decimal('90'))],
        verbose_name='위도',
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7,
        validators=[MinValueValidator(Decimal('-180')), MaxValueValidator(Decimal('180'))],
        verbose_name='경도',
    )
    kakao_place_id = models.CharField(
        max_length=32, unique=True, null=True, blank=True, verbose_name='카카오 장소 ID',
    )
    kakao_place_url = models.URLField(blank=True, verbose_name='카카오맵 링크')
    kakao_category = models.CharField(max_length=100, blank=True, verbose_name='카카오 카테고리')
    tags = models.ManyToManyField(PlaceTag, blank=True, related_name='places', verbose_name='태그')
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
        db_table = 'places_place'
        ordering = ['-created_at']
        verbose_name = '장소'
        verbose_name_plural = '장소 목록'

    def __str__(self) -> str:
        return self.name


class PlaceSuggestion(models.Model):
    """방문자가 새 장소를 제보하는 검토 대기 큐."""

    restaurant_name = models.CharField(max_length=100, verbose_name='제보 상호명')
    kakao_place_url = models.URLField(blank=True, verbose_name='카카오맵 링크')
    message = models.TextField(blank=True, verbose_name='추천 이유')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='place_suggestions', verbose_name='제보자',
    )
    is_reviewed = models.BooleanField(default=False, verbose_name='검토 완료')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'places_place_suggestion'
        ordering = ['-created_at']
        verbose_name = '장소 제보'
        verbose_name_plural = '장소 제보 목록'

    def __str__(self) -> str:
        return f'{self.restaurant_name} ({self.submitted_by})'


class PlaceSyncFolder(models.Model):
    """카카오맵 즐겨찾기 폴더 ↔ Place.category 매핑. 활성화된 폴더만 동기화 대상이 된다."""

    category = models.CharField(max_length=20, choices=Place.Category.choices, verbose_name='카테고리')
    kakao_folder_id = models.CharField(max_length=32, verbose_name='카카오 폴더 ID')
    title = models.CharField(max_length=100, blank=True, verbose_name='폴더 제목 (참고용)')
    is_active = models.BooleanField(default=True, verbose_name='동기화 활성화')
    last_synced_at = models.DateTimeField(null=True, blank=True, verbose_name='마지막 동기화 시각')

    class Meta:
        db_table = 'places_sync_folder'
        ordering = ['category']
        verbose_name = '장소 동기화 폴더'
        verbose_name_plural = '장소 동기화 폴더 목록'

    def __str__(self) -> str:
        return self.title or self.kakao_folder_id
