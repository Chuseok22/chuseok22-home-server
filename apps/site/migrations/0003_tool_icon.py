from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0002_seed_tools'),
    ]

    operations = [
        migrations.AddField(
            model_name='tool',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=8, verbose_name='아이콘(이모지)'),
        ),
    ]
