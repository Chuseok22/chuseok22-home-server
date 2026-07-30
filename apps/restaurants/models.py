from django.core.exceptions import ValidationError
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
