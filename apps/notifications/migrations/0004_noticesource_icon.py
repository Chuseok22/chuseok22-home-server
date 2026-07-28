from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0003_remove_noticesource_telegram_chat_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='noticesource',
            name='icon',
            field=models.CharField(blank=True, default='', max_length=8, verbose_name='아이콘(이모지)'),
        ),
    ]
