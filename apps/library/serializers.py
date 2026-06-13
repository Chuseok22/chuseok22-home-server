from datetime import datetime

from rest_framework import serializers


class RoomSlotSerializer(serializers.Serializer):
    time_label = serializers.CharField()
    is_available = serializers.BooleanField()
    room_no = serializers.CharField(allow_null=True, default=None)
    room_name = serializers.CharField(allow_null=True, default=None)
    start_time = serializers.CharField(allow_null=True, default=None)


class StudyRoomSerializer(serializers.Serializer):
    room_name = serializers.CharField()
    group_title = serializers.CharField()
    seat_cnt = serializers.IntegerField()
    slots = RoomSlotSerializer(many=True)


class AttendeeInputSerializer(serializers.Serializer):
    student_id = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=50)


class StudyRoomReserveRequestSerializer(serializers.Serializer):
    # auto_select=False 시 필수
    room_no = serializers.CharField(max_length=10, required=False)
    room_gb = serializers.CharField(max_length=10, required=False)
    seat_cnt = serializers.IntegerField(required=False, min_value=1)
    sroom_title = serializers.CharField(max_length=100, required=False)
    room_name = serializers.CharField(max_length=100, required=False)
    seq = serializers.CharField(max_length=5, required=False)

    reserve_date = serializers.RegexField(r'^\d{8}$')   # YYYYMMDD
    start_time = serializers.RegexField(r'^\d{4}$')     # HHMM
    use_time = serializers.ChoiceField(choices=[60, 120])
    auto_select = serializers.BooleanField(default=False)
    attendees = AttendeeInputSerializer(many=True)

    def validate_reserve_date(self, value: str) -> str:
        try:
            datetime.strptime(value, '%Y%m%d')
        except ValueError:
            raise serializers.ValidationError('reserve_date는 유효한 YYYYMMDD여야 합니다.')
        return value

    def validate_start_time(self, value: str) -> str:
        try:
            datetime.strptime(value, '%H%M')
        except ValueError:
            raise serializers.ValidationError('start_time은 유효한 HHMM이어야 합니다.')
        return value

    def validate_attendees(self, value: list[dict]) -> list[dict]:
        if len(value) < 1:
            raise serializers.ValidationError('참여자는 최소 1명이어야 합니다.')
        return value

    def validate(self, data: dict) -> dict:
        if not data.get('auto_select'):
            required = ['room_no', 'room_gb', 'seat_cnt', 'sroom_title', 'room_name', 'seq']
            missing = [f for f in required if f not in data]
            if missing:
                raise serializers.ValidationError(
                    f'auto_select=false 시 필수 필드: {", ".join(missing)}'
                )
        return data


class StudyRoomReserveResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    result_code = serializers.CharField()
    result_message = serializers.CharField()
    room_no = serializers.CharField()
    room_name = serializers.CharField()


class ReservationAttendeeSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    student_id = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=50)
    created_at = serializers.DateTimeField(read_only=True)
