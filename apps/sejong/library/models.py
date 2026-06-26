from django.db import models


class ReservationAttendee(models.Model):
    """예약 참여자. student_id는 고유하며 중복 저장하지 않는다."""

    student_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'library_reservation_attendee'
        ordering = ['name']

    def __str__(self) -> str:
        return f'{self.name} ({self.student_id})'


class ReservationHistory(models.Model):
    """예약 요청 이력. 성공/실패 여부와 관계없이 모든 요청을 저장한다."""

    room_no = models.CharField(max_length=10)
    room_name = models.CharField(max_length=100)
    reserve_date = models.CharField(max_length=8)    # YYYYMMDD
    start_time = models.CharField(max_length=4)      # HHMM
    use_time = models.IntegerField()                 # 60 or 120
    attendees_json = models.JSONField()              # [{"student_id": ..., "name": ...}]
    result_code = models.CharField(max_length=10)
    result_message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'library_reservation_history'
        ordering = ['-created_at']
