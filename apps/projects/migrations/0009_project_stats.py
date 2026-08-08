from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0008_project_is_featured'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='stats',
            field=models.JSONField(blank=True, default=list, verbose_name='핵심 지표'),
        ),
    ]
