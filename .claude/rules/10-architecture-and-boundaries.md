# Architecture And Boundaries

## High-level architecture

```
[클라이언트 / 크론 스케줄러]
          ↓
    Django 앱 레이어
    ┌──────────────────────────────────────┐
    │  views / management commands         │
    │     ↓              ↓                 │
    │  serializers     services/           │
    │     ↓              ↓                 │
    │  models (ORM)   외부 API 호출          │
    └──────────────────────────────────────┘
          ↓
    PostgreSQL (production)
```

- **외부 시스템 연동은 `services/` 레이어에서만 수행**한다.
- management command는 전체 흐름을 조율하되 세부 로직은 직접 구현하지 않는다.
- REST API: DRF `APIView` / `@api_view`, JWT 인증 (`SimpleJWT`)

## Module boundaries

| 계층 | 책임 | 금지 사항 |
|---|---|---|
| `views.py` / `@api_view` | HTTP 요청/응답 처리 | 비즈니스 로직 직접 구현 금지 |
| `serializers.py` | 입력 검증, 직렬화 | DB 직접 접근 금지 |
| `services/` | 외부 API 연동, 비즈니스 로직 | HTTP 요청/응답 파싱 금지 |
| `models.py` | 스키마 정의, ORM | 비즈니스 로직 금지 |
| `management/commands/` | 배치·스케줄 작업 흐름 조율 | HTTP 엔드포인트 로직 금지 |
| `apps/core/` | 인프라성 엔드포인트 (헬스체크 등) | 도메인 로직 금지 |

**허용 의존 방향**: `views → services → models`, `commands → services → models`

**금지 의존 관계**: `models → services`, `services → views`, 앱 간 직접 model import

## Data flow

**REST API 흐름:**
```
HTTP 요청 → urls.py → views.py → serializers (검증) → services / ORM → 응답
```

**Management command 흐름:**
```
command.handle() → 조건 조회 (ORM) → services 호출 → 결과 저장 (ORM)
```

**설정 로딩:**
```
production.py → .env.production → base.py (env() 호출)
development.py → .env.local   → base.py (env() 호출)
```

## File / folder conventions

- **새 도메인 앱 추가**: `apps/<domain>/` 디렉터리 생성 → `LOCAL_APPS`에 등록
- **새 외부 서비스 추가**: `apps/<domain>/services/<service>.py` 생성
- **새 management command**: `apps/<domain>/management/commands/<name>.py`
- **URL 등록**: `apps/<domain>/urls.py` → `config/urls.py`에 `include()`로 연결
- **마이그레이션**: `python manage.py makemigrations` 자동 생성, 직접 수정 금지

## Extension points

**새 도메인 앱 추가 패턴:**
```python
# 1. apps/<domain>/ 디렉터리 구조 생성
# 2. config/settings/base.py
LOCAL_APPS = [
    'apps.core',
    'apps.notifications',
    'apps.<new_domain>',  # ← 추가
]

# 3. config/urls.py
urlpatterns += [
    path('api/v1/<domain>/', include('apps.<domain>.urls')),
]
```

**현재 앱별 URL prefix:**
```
/admin/                  - Django Admin
/api/v1/health/          - 헬스체크
/api/v1/auth/token/      - JWT 발급
/api/v1/auth/token/refresh/ - JWT 갱신
/docs/swagger/           - Swagger UI
```
