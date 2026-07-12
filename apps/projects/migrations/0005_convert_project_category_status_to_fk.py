import django.db.models.deletion
from django.db import migrations, models

CATEGORY_VALUE_TO_NAME = {
    'team': '팀 프로젝트',
    'side': '사이드 프로젝트',
    'open_source': '오픈소스',
}

STATUS_VALUE_TO_NAME = {
    'in_progress': '진행중',
    'completed': '완료',
    'archived': '중단',
}


def populate_category_and_status_fk(apps, schema_editor) -> None:
    """기존 CharField(category/status) 문자열 값을 새 FK(category_new/status_new)로 이관한다.
    이 마이그레이션은 되돌릴 수 없다 — 역방향 실행 시 FK 값을 문자열로 복원하지 않는다."""
    Project = apps.get_model('projects', 'Project')
    ProjectCategory = apps.get_model('projects', 'ProjectCategory')
    ProjectStatus = apps.get_model('projects', 'ProjectStatus')

    categories = {obj.name: obj for obj in ProjectCategory.objects.all()}
    statuses = {obj.name: obj for obj in ProjectStatus.objects.all()}

    for project in Project.objects.all():
        project.category_new = categories[CATEGORY_VALUE_TO_NAME[project.category]]
        project.status_new = statuses[STATUS_VALUE_TO_NAME[project.status]]
        project.save(update_fields=['category_new', 'status_new'])


def reverse_noop(apps, schema_editor) -> None:
    # RunPython 데이터 이관만 no-op으로 되돌린다. 이 마이그레이션의 스키마 오퍼레이션
    # (RemoveField/RenameField 등)은 자동 역방향이 시도되며, 이미 값이 채워진 컬럼에
    # NOT NULL CharField를 기본값 없이 재생성하려 해 실패할 수 있다. 즉 이 마이그레이션
    # 전체는 사실상 되돌릴 수 없다고 간주한다 — 필요 시 DB 백업에서 복원한다.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_seed_project_category_and_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='category_new',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='projects',
                to='projects.projectcategory',
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='status_new',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='projects',
                to='projects.projectstatus',
            ),
        ),
        migrations.RunPython(populate_category_and_status_fk, reverse_noop),
        migrations.RemoveField(model_name='project', name='category'),
        migrations.RemoveField(model_name='project', name='status'),
        migrations.RenameField(model_name='project', old_name='category_new', new_name='category'),
        migrations.RenameField(model_name='project', old_name='status_new', new_name='status'),
        migrations.AlterField(
            model_name='project',
            name='category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='projects',
                to='projects.projectcategory',
            ),
        ),
        migrations.AlterField(
            model_name='project',
            name='status',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='projects',
                to='projects.projectstatus',
            ),
        ),
        migrations.AlterModelOptions(
            name='project',
            options={'ordering': ['category__order', 'order', '-created_at']},
        ),
    ]
