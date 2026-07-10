from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_alter_category_slug_alter_post_slug'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='이름')),
                ('slug', models.SlugField(blank=True, unique=True, verbose_name='슬러그')),
            ],
            options={
                'verbose_name': '태그',
                'verbose_name_plural': '태그 목록',
                'db_table': 'blog_tag',
                'ordering': ['name'],
            },
        ),
        migrations.AddConstraint(
            model_name='tag',
            constraint=models.UniqueConstraint(Lower('name'), name='unique_tag_name_ci'),
        ),
    ]
