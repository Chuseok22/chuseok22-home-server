from django.db import migrations, models


def migrate_tags_forward(apps, schema_editor) -> None:
    """기존 JSONField(tags_json)의 문자열 리스트를 Tag M2M으로 이관한다.
    실제 앱 코드(get_or_create_tags)를 가져다 쓰되 tag_model에 historical Tag를 주입해
    커스텀 clean()/save()를 우회한다. 이 함수의 정규화 로직이 나중에 바뀌면 이 마이그레이션을
    새 DB에 처음부터 재생할 때 당시와 다르게 동작할 수 있다 — 개인 프로젝트 규모라 감수한다."""
    from apps.blog.services.tags import get_or_create_tags

    Post = apps.get_model('blog', 'Post')
    Tag = apps.get_model('blog', 'Tag')
    for post in Post.objects.all():
        tags = get_or_create_tags(post.tags_json or [], tag_model=Tag)
        post.tags.set(tags)


def migrate_tags_backward(apps, schema_editor) -> None:
    # RemoveField의 reverse(재추가)는 컬럼만 복원하고 값은 복원하지 못하므로
    # 이 마이그레이션은 되돌리기(migrate blog 0005)를 지원하지 않는다.
    # 필요 시 DB 백업에서 복원한다.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0005_rename_post_tags_to_tags_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='posts', to='blog.tag', verbose_name='태그'),
        ),
        migrations.RunPython(migrate_tags_forward, migrate_tags_backward),
        migrations.RemoveField(
            model_name='post',
            name='tags_json',
        ),
    ]
