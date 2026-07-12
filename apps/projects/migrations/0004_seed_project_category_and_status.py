from django.db import migrations


def seed_categories_and_statuses(apps, schema_editor) -> None:
    ProjectCategory = apps.get_model('projects', 'ProjectCategory')
    ProjectStatus = apps.get_model('projects', 'ProjectStatus')

    for order, name in enumerate(['팀 프로젝트', '사이드 프로젝트', '오픈소스']):
        ProjectCategory.objects.create(name=name, order=order)

    for order, name in enumerate(['진행중', '완료', '중단']):
        ProjectStatus.objects.create(name=name, order=order)


def remove_seeded_categories_and_statuses(apps, schema_editor) -> None:
    ProjectCategory = apps.get_model('projects', 'ProjectCategory')
    ProjectStatus = apps.get_model('projects', 'ProjectStatus')
    ProjectCategory.objects.filter(name__in=['팀 프로젝트', '사이드 프로젝트', '오픈소스']).delete()
    ProjectStatus.objects.filter(name__in=['진행중', '완료', '중단']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_projectcategory_projectstatus'),
    ]

    operations = [
        migrations.RunPython(seed_categories_and_statuses, remove_seeded_categories_and_statuses),
    ]
