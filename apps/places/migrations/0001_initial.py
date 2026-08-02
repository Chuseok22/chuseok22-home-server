import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlaceTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='이름')),
                ('slug', models.SlugField(blank=True, unique=True, verbose_name='슬러그')),
            ],
            options={
                'verbose_name': '장소 태그',
                'verbose_name_plural': '장소 태그 목록',
                'db_table': 'places_place_tag',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Place',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='상호명')),
                ('category', models.CharField(
                    choices=[
                        ('restaurant', '맛집'), ('cafe', '카페'), ('bar', '바'),
                        ('date_course', '데이트코스'), ('accommodation', '숙소'),
                    ],
                    default='restaurant', max_length=20, verbose_name='카테고리',
                )),
                ('address', models.CharField(blank=True, max_length=255, verbose_name='지번 주소')),
                ('road_address', models.CharField(blank=True, max_length=255, verbose_name='도로명 주소')),
                ('latitude', models.DecimalField(
                    decimal_places=7, max_digits=10,
                    validators=[
                        django.core.validators.MinValueValidator(Decimal('-90')),
                        django.core.validators.MaxValueValidator(Decimal('90')),
                    ],
                    verbose_name='위도',
                )),
                ('longitude', models.DecimalField(
                    decimal_places=7, max_digits=10,
                    validators=[
                        django.core.validators.MinValueValidator(Decimal('-180')),
                        django.core.validators.MaxValueValidator(Decimal('180')),
                    ],
                    verbose_name='경도',
                )),
                ('kakao_place_id', models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='카카오 장소 ID')),
                ('kakao_place_url', models.URLField(blank=True, verbose_name='카카오맵 링크')),
                ('kakao_category', models.CharField(blank=True, max_length=100, verbose_name='카카오 카테고리')),
                ('meal_time', models.CharField(
                    choices=[('breakfast', '아침'), ('lunch', '점심'), ('dinner', '저녁'), ('all_day', '상시')],
                    default='all_day', max_length=20, verbose_name='식사 시간대',
                )),
                ('personal_rating', models.PositiveSmallIntegerField(
                    blank=True, null=True,
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(5),
                    ],
                    verbose_name='개인 평점',
                )),
                ('personal_review', models.CharField(blank=True, max_length=200, verbose_name='한줄 평')),
                ('note', models.TextField(blank=True, verbose_name='비고')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tags', models.ManyToManyField(blank=True, related_name='places', to='places.placetag', verbose_name='태그')),
            ],
            options={
                'verbose_name': '장소',
                'verbose_name_plural': '장소 목록',
                'db_table': 'places_place',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PlaceSuggestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('restaurant_name', models.CharField(max_length=100, verbose_name='제보 상호명')),
                ('kakao_place_url', models.URLField(blank=True, verbose_name='카카오맵 링크')),
                ('message', models.TextField(blank=True, verbose_name='추천 이유')),
                ('is_reviewed', models.BooleanField(default=False, verbose_name='검토 완료')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('submitted_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='place_suggestions',
                    to=settings.AUTH_USER_MODEL, verbose_name='제보자',
                )),
            ],
            options={
                'verbose_name': '장소 제보',
                'verbose_name_plural': '장소 제보 목록',
                'db_table': 'places_place_suggestion',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='placetag',
            constraint=models.UniqueConstraint(Lower('name'), name='unique_place_tag_name_ci'),
        ),
    ]
