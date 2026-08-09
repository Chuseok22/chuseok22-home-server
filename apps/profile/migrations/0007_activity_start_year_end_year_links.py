from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0006_alter_skill_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='start_year',
            field=models.PositiveSmallIntegerField(default=2024, verbose_name='시작 연도'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='activity',
            name='end_year',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='종료 연도'),
        ),
        migrations.AddField(
            model_name='activity',
            name='links',
            field=models.JSONField(
                blank=True, default=list,
                help_text=(
                    '예: [{"type": "github", "url": "https://..."}]. '
                    'type은 official/github/youtube/instagram/linkedin/presentation/article/other 중 하나.'
                ),
                verbose_name='관련 링크 목록',
            ),
        ),
    ]
