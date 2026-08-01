import logging

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
        cursor.execute(
            'INSERT INTO places_place ('
            '  id, name, category, address, road_address, latitude, longitude, '
            '  kakao_place_id, kakao_place_url, kakao_category, meal_time, '
            '  personal_rating, personal_review, note, created_at, updated_at'
            ') SELECT '
            '  id, name, category, address, road_address, latitude, longitude, '
            '  kakao_place_id, kakao_place_url, kakao_category, meal_time, '
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
