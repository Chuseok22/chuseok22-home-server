from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.profile.models import ActivityAttachment


@receiver(post_delete, sender=ActivityAttachment)
def delete_activity_attachment_file(sender: type[ActivityAttachment], instance: ActivityAttachment, **kwargs: object) -> None:
    # Activity가 삭제되어 CASCADE로 함께 지워지는 경우에도 post_delete는 각 인스턴스마다
    # 발동하므로(개별 delete()를 오버라이드하는 것보다 안전), 두 삭제 경로 모두 파일을 정리한다.
    instance.file.delete(save=False)
