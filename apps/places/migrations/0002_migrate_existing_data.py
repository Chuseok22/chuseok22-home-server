import logging
from urllib.parse import urlsplit

from django.db import migrations

logger = logging.getLogger(__name__)


def migrate_existing_data(apps, schema_editor) -> None:
    existing_tables = schema_editor.connection.introspection.table_names()
    if 'restaurants_restaurant' not in existing_tables:
        logger.info('restaurants_restaurant 테이블 없음 — 신규 DB로 판단, 데이터 이관을 건너뜁니다.')
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO places_place_tag (id, name, slug) '
            'SELECT id, name, slug FROM restaurants_restaurant_tag'
        )
        # 운영 DB는 이 시점에도 0004 상태(kakao_place_id/kakao_category 없음, category는
        # 옛 카카오 업종 문자열)다 — 신규 category는 기본값 'restaurant'로, kakao_category는
        # 옛 category 컬럼값으로 채운다. kakao_place_id는 아래에서 ORM으로 별도 백필한다.
        cursor.execute(
            'INSERT INTO places_place ('
            '  id, name, category, address, road_address, latitude, longitude, '
            '  kakao_place_url, kakao_category, meal_time, '
            '  personal_rating, personal_review, note, created_at, updated_at'
            ') SELECT '
            "  id, name, 'restaurant', address, road_address, latitude, longitude, "
            '  kakao_place_url, category, meal_time, '
            '  personal_rating, personal_review, note, created_at, updated_at'
            ' FROM restaurants_restaurant'
        )
        cursor.execute(
            'INSERT INTO places_place_suggestion ('
            '  id, restaurant_name, kakao_place_url, message, submitted_by_id, is_reviewed, created_at'
            ') SELECT '
            '  id, restaurant_name, kakao_place_url, message, submitted_by_id, is_reviewed, created_at '
            'FROM restaurants_restaurant_suggestion'
        )
        cursor.execute(
            'INSERT INTO places_place_tags (id, place_id, placetag_id) '
            'SELECT id, restaurant_id, restauranttag_id FROM restaurants_restaurant_tags'
        )

        for table, column in (
            ('places_place_tag', 'id'), ('places_place', 'id'),
            ('places_place_suggestion', 'id'), ('places_place_tags', 'id'),
        ):
            cursor.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', '{column}'), "
                f"COALESCE((SELECT MAX({column}) FROM {table}), 1), "
                f"(SELECT MAX({column}) FROM {table}) IS NOT NULL)"
            )

        cursor.execute('DROP TABLE restaurants_restaurant_tags')
        cursor.execute('DROP TABLE restaurants_restaurant_suggestion')
        cursor.execute('DROP TABLE restaurants_restaurant')
        cursor.execute('DROP TABLE restaurants_restaurant_tag')

    # kakao_place_id 백필: kakao_place_url에서 ID를 역파싱한다(Task 1의 0005 마이그레이션과
    # 동일한 로직 — 중복 URL·비숫자 경로는 건너뛴다).
    Place = apps.get_model('places', 'Place')
    for place in Place.objects.exclude(kakao_place_url=''):
        place_id = urlsplit(place.kakao_place_url).path.lstrip('/')
        if not place_id.isdecimal():
            logger.warning(
                '카카오 장소 ID 백필 건너뜀 (숫자 아님): place_id=%s, url=%s', place.pk, place.kakao_place_url,
            )
            continue
        if Place.objects.filter(kakao_place_id=place_id).exclude(pk=place.pk).exists():
            logger.warning(
                '카카오 장소 ID 백필 건너뜀 (중복): place_id=%s, kakao_place_id=%s', place.pk, place_id,
            )
            continue
        place.kakao_place_id = place_id
        place.save(update_fields=['kakao_place_id'])

    ContentType = apps.get_model('contenttypes', 'ContentType')
    for old_model, new_model in (
        ('restaurant', 'place'), ('restauranttag', 'placetag'), ('restaurantsuggestion', 'placesuggestion'),
    ):
        ContentType.objects.filter(app_label='restaurants', model=old_model).update(
            app_label='places', model=new_model,
        )


def reverse_noop(apps, schema_editor) -> None:
    # 데이터 이관을 역방향으로 되돌리는 것은 지원하지 않는다 — 필요 시 DB 백업에서 복구한다.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('places', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(migrate_existing_data, reverse_noop),
    ]
