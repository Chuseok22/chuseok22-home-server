import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='GithubActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(max_length=50, unique=True, verbose_name='이벤트 ID')),
                ('event_type', models.CharField(max_length=50, verbose_name='이벤트 유형')),
                ('repo_name', models.CharField(max_length=200, verbose_name='저장소 이름')),
                ('title', models.CharField(max_length=200, verbose_name='표시 제목')),
                ('meta', models.CharField(max_length=500, verbose_name='표시 설명')),
                ('occurred_at', models.DateTimeField(db_index=True, verbose_name='이벤트 발생 시각')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='DB 수집 시각')),
            ],
            options={
                'verbose_name': 'GitHub 활동',
                'verbose_name_plural': 'GitHub 활동 목록',
                'ordering': ('-occurred_at',),
            },
        ),
    ]
