# API Documentation

## 원칙

모든 API 엔드포인트는 `drf-spectacular`의 `extend_schema` 데코레이터를 통해 Swagger 문서를 제공한다.
프론트엔드 개발자가 Swagger Docs만 보고 개발할 수 있어야 한다.

## 필수 항목

새 뷰 메서드를 추가하거나 기존 메서드를 수정할 때 아래 항목을 빠짐없이 작성한다.

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

@extend_schema(
    summary='한 줄 요약 (동사+목적어)',
    description='상세 설명. 분기 조건·제약·부작용을 포함한다.',
    parameters=[...],       # 쿼리/경로 파라미터가 있을 때
    request=RequestSerializer,
    responses={
        200: ResponseSerializer,
        400: OpenApiResponse(description='입력 검증 오류'),
        422: ResponseSerializer,   # 비즈니스 로직 실패
        503: OpenApiResponse(description='외부 서비스 오류'),
    },
)
def post(self, request: Request) -> Response: ...
```

## 항목별 작성 기준

| 항목 | 기준 |
|---|---|
| `summary` | 동사+목적어 형태. 예: `스터디룸 예약`, `참여자 삭제` |
| `description` | 분기(auto_select 등), 필수 필드 조건, HTTP 상태코드 의미, 부작용(DB 저장 등) 명시 |
| `parameters` | 쿼리·경로 파라미터 전부 기술. `required`, `description`, 예시 포함 |
| `request` | 요청 Serializer 명시. 분기에 따라 일부 필드가 선택적이면 description에 설명 |
| `responses` | 성공(200/201/204)과 실패(400/422/503) 모두 기술. 실패도 body 구조가 있으면 Serializer 사용 |

## 상태코드 규칙

| 코드 | 사용 |
|---|---|
| 200 | 조회 성공, 기존 리소스 반환 (get_or_create 등) |
| 201 | 신규 리소스 생성 성공 |
| 204 | 삭제 성공 (body 없음) |
| 400 | 입력 검증 실패 (Serializer validation error) |
| 422 | 요청은 유효하나 비즈니스 로직 실패 (예약 불가, 가용 룸 없음 등) |
| 503 | 외부 서비스 오류 (학술정보원 응답 없음, 환경변수 미설정 등) |

## 검증 명령

```bash
python manage.py spectacular --validate --settings=config.settings.development
```

`Errors: 0` 이 아니면 수정 후 커밋한다 (기존 `health_check` 뷰 오류는 예외).

## 리뷰 체크리스트

- [ ] 새로 추가된 모든 뷰 메서드에 `@extend_schema` 있는가
- [ ] `summary`, `description` 작성되었는가
- [ ] 성공/실패 응답 코드가 모두 기술되었는가
- [ ] `spectacular --validate` 통과했는가
