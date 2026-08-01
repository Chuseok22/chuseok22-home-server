from urllib.parse import urlsplit

from django.db import migrations, models


def backfill_kakao_place_id(apps, schema_editor):
    # 기존 kakao_place_url("https://place.map.kakao.com/{id}")에서 ID를 역파싱해 채운다.
    # kakao_place_id는 unique=True라, 같은 URL을 가진 레코드가 2건 이상이면 두 번째부터
    # IntegrityError로 마이그레이션 전체가 롤백된다 — 그런 레코드는 조용히 건너뛴다(로그만 남김).
    # path가 숫자가 아니면(예: link/map/... 형태의 옛 URL) kakao_place_id(max_length=32)에
    # 안전하지 않으므로 이것도 건너뛴다.
    import logging

    logger = logging.getLogger(__name__)
    Restaurant = apps.get_model('restaurants', 'Restaurant')
    for restaurant in Restaurant.objects.exclude(kakao_place_url=''):
        place_id = urlsplit(restaurant.kakao_place_url).path.lstrip('/')
        if not place_id.isdecimal():
            logger.warning(
                '카카오 장소 ID 백필 건너뜀 (숫자 아님): restaurant_id=%s, url=%s',
                restaurant.pk, restaurant.kakao_place_url,
            )
            continue
        if Restaurant.objects.filter(kakao_place_id=place_id).exclude(pk=restaurant.pk).exists():
            logger.warning(
                '카카오 장소 ID 백필 건너뜀 (중복): restaurant_id=%s, place_id=%s',
                restaurant.pk, place_id,
            )
            continue
        restaurant.kakao_place_id = place_id
        restaurant.save(update_fields=['kakao_place_id'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('restaurants', '0004_alter_restaurant_latitude_alter_restaurant_longitude'),
    ]

    operations = [
        migrations.RenameField(model_name='restaurant', old_name='category', new_name='kakao_category'),
        migrations.AddField(
            model_name='restaurant',
            name='category',
            field=models.CharField(
                choices=[
                    ('restaurant', '맛집'), ('cafe', '카페'), ('bar', '바'),
                    ('date_course', '데이트코스'), ('accommodation', '숙소'),
                ],
                default='restaurant', max_length=20, verbose_name='카테고리',
            ),
        ),
        migrations.AddField(
            model_name='restaurant',
            name='kakao_place_id',
            field=models.CharField(
                blank=True, max_length=32, null=True, unique=True, verbose_name='카카오 장소 ID',
            ),
        ),
        migrations.RunPython(backfill_kakao_place_id, noop_reverse),
    ]
