from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('places', '0002_migrate_existing_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlaceSyncFolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(
                    choices=[
                        ('restaurant', '맛집'), ('cafe', '카페'), ('bar', '바'),
                        ('date_course', '데이트코스'), ('accommodation', '숙소'),
                    ],
                    max_length=20, verbose_name='카테고리',
                )),
                ('kakao_folder_id', models.CharField(max_length=32, verbose_name='카카오 폴더 ID')),
                ('title', models.CharField(blank=True, max_length=100, verbose_name='폴더 제목 (참고용)')),
                ('is_active', models.BooleanField(default=True, verbose_name='동기화 활성화')),
                ('last_synced_at', models.DateTimeField(blank=True, null=True, verbose_name='마지막 동기화 시각')),
            ],
            options={
                'verbose_name': '장소 동기화 폴더',
                'verbose_name_plural': '장소 동기화 폴더 목록',
                'db_table': 'places_sync_folder',
                'ordering': ['category'],
            },
        ),
    ]
