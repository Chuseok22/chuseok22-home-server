# Team Conventions

## Naming

- **변수·함수명**: snake_case
- **클래스명**: PascalCase
- **URL 네임**: kebab-case (`token-refresh`, `health-check`)
- **앱명**: `apps.<domain>` 형식 소문자 (`apps.notifications`, `apps.core`)
- **management command 파일명**: snake_case 동사_명사 (`check_new_notices`, `seed_notices`)
- **축약 금지**: `src` → `source`, `msg` → `message`, `req` → `request`

## Code style

- **타입 힌트**: 모든 함수 시그니처에 명시
  ```python
  def send_notice(self, source: NoticeSource, notice: Notice) -> bool: ...
  ```
- `-> None` 반환 함수도 명시
- **`any` 타입 사용 금지**
- **deprecated API 금지** — Django 5.1 기준
- **로깅**:
  - 서비스·크롤러 등 내부 로직: `logging.getLogger(__name__)` 사용
  - management command: `self.stdout.write()` / `self.stderr.write()` 사용
  - `print()` 절대 사용 금지
- **에러 처리**:
  - 외부 API 호출 실패 → `logger.error()` + 안전한 기본값 반환 (예외 전파 금지)
  - 잘못된 입력 → 예외 발생이 아닌 명시적 반환값 처리
- **주석**: 한국어, 비자명한 결정·제약·우회책에만 작성. 코드 재서술 금지

## Responsibility separation

| 계층 | 역할 | 예시 파일 |
|---|---|---|
| `views.py` | HTTP 요청 수신, 직렬화, 응답 반환 | `apps/core/views.py` |
| `serializers.py` | 입력 검증 및 변환 | — |
| `services/` | 외부 API 연동, 핵심 비즈니스 로직 | `apps/notifications/services/telegram.py` |
| `models.py` | 스키마 정의, ORM 조작 | `apps/notifications/models.py` |
| `management/commands/` | 배치 흐름 조율 (조회 → 처리 → 저장) | `check_new_notices.py` |

비즈니스 로직 위치 기준:
- 단순 CRUD → `views.py`에서 ORM 직접 사용 허용
- 외부 API 호출 포함 → 반드시 `services/` 분리
- 여러 모델·서비스를 조율하는 복잡한 흐름 → `management/commands/` 또는 별도 서비스 클래스

## Review expectations

반드시 확인할 항목:
- [ ] 새 앱이 `LOCAL_APPS`에 등록되었는가
- [ ] 외부 API 연동이 `services/` 레이어에 분리되었는가
- [ ] 타입 힌트가 모든 함수에 있는가
- [ ] `print()` 대신 `logger` 또는 `self.stdout.write()`를 사용하는가
- [ ] 중복 처리 방지 로직이 있는가 (발송·처리 이력 관련)

block 기준:
- 외부 API 키·시크릿 하드코딩
- `.env` 파일 커밋
- 서비스 레이어 없이 뷰에서 외부 API 직접 호출
