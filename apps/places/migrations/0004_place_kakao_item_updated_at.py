from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('places', '0003_placesyncfolder'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='kakao_item_updated_at',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='카카오 즐겨찾기 최종 수정 시각(원본)'),
            preserve_default=False,
        ),
    ]
