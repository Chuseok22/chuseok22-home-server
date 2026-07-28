from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_alter_projectcategory_options_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='project',
            old_name='demo_href',
            new_name='web_site_href',
        ),
        migrations.AddField(
            model_name='project',
            name='ios_href',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='project',
            name='android_href',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='project',
            name='extra_links',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
