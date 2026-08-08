from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profile', '0005_seed_awards_and_activities'),
    ]

    operations = [
        migrations.AlterField(
            model_name='skill',
            name='category',
            field=models.CharField(
                choices=[
                    ('backend', 'Backend'),
                    ('mobile', 'Mobile'),
                    ('frontend', 'Frontend'),
                    ('database', 'Database'),
                    ('infra', 'Infra'),
                    ('ai', 'AI'),
                    ('tool', 'Tool'),
                    ('etc', 'ETC'),
                ],
                max_length=20,
                verbose_name='분류',
            ),
        ),
    ]
