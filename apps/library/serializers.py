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
