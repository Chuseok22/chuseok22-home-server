from rest_framework import serializers

from apps.sejong.student.services.student_search import StudentInfo


class StudentInfoSerializer(serializers.Serializer):
    student_no = serializers.CharField()
    name = serializers.CharField()
    dept_cd = serializers.CharField()
    dept_name = serializers.CharField()
    # EmailField 대신 CharField — classic 응답이 비정상 형식(빈 문자열 등)을 줄 경우 검증 예외 방지
    # allow_null=True: email 필드 누락 시 None 정규화 허용
    email = serializers.CharField(allow_blank=True, allow_null=True)
    double_dept_name = serializers.CharField(allow_null=True, allow_blank=True)

    def to_representation(self, instance: StudentInfo) -> dict:  # type: ignore[override]
        return {
            'student_no': instance.student_no,
            'name': instance.name,
            'dept_cd': instance.dept_cd,
            'dept_name': instance.dept_name,
            'email': instance.email,
            'double_dept_name': instance.double_dept_name,
        }


class StudentSearchResponseSerializer(serializers.Serializer):
    results = StudentInfoSerializer(many=True)
