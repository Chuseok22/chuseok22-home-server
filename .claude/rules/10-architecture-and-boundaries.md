# Architecture And Boundaries

## High-level architecture

```
[클라이언트 / 인앱 스케줄러(apps.core, django-apscheduler) / 외부 크론]
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
    PostgreSQL
```

- **외부 시스템 연동은 `services/` 레이어에서만 수행**한다.
- management command는 전체 흐름을 조율하되 세부 로직은 직접 구현하지 않는다.
- REST API: DRF `APIView` / `@api_view`, JWT 인증 (`SimpleJWT`)
- 주기 실행 작업은 외부 크론이 아니라 `apps.core`의 `django-apscheduler` 기반 인앱 스케줄러(`scheduler.py`, `ScheduledJobConfig` 모델)로 등록·관리한다. 새 주기 작업 추가 시 이 스케줄러에 등록하고, 별도 시스템 크론을 새로 만들지 않는다.

## Module boundaries

| 계층 | 책임 | 금지 사항 |
|---|---|---|
| `views.py` / `@api_view` | HTTP 요청/응답 처리 | 비즈니스 로직 직접 구현 금지 |
| `serializers.py` | 입력 검증, 직렬화 | DB 직접 접근 금지 |
| `services/` | 외부 API 연동, 비즈니스 로직 | HTTP 요청/응답 파싱 금지 |
| `models.py` | 스키마 정의, ORM | 비즈니스 로직 금지 |
| `management/commands/` | 배치·스케줄 작업 흐름 조율 | HTTP 엔드포인트 로직 금지 |
| `apps/core/` | 인프라성 엔드포인트(헬스체크 등), django-apscheduler 기반 인앱 스케줄러 관리 | 도메인 로직 금지 |
| `apps/notifications/crawlers/` | 공지·공모전 등 외부 소스별 크롤러 구현체(`base.py` 공통 인터페이스, `registry.py`로 등록) | `services/`가 호출하는 하위 구현 레이어이며, 이 레이어를 우회해 크롤링 로직을 `services/`나 `views.py`에 직접 작성하지 않는다 |

**허용 의존 방향**: `views → services → models`, `commands → services → models`, `services → crawlers/`(notifications 한정)

**금지 의존 관계**: `models → services`, `services → views`, 앱 간 직접 model import

**예외 — SSR 표현 계층(`apps.site`)**: Issue #25(SSR 마이그레이션)에서 `apps.site`는 REST API
레이어 없이 뷰가 각 도메인 앱의 `models`(조회)와 `services/`(외부 연동·쓰기)를 직접 호출하는
구조로 설계됐다(`docs/superpowers/plans/2026-07-05-site-ssr-migration.md` Architecture 절 참고).
`apps.site.views → apps.blog/projects/engagement/sejong.*.models`처럼 표현 계층이 도메인 모델을
직접 조회하는 것은 이 예외에 한해 허용한다. 그 외 앱 간 직접 model import는 여전히 금지다.

**예외 — `apps.sejong.auth`(도메인 네임스페이스 내 공용 인증 서비스)**: `apps.sejong` 네임스페이스는
`library`/`student`/`auth` 세 하위 패키지로 나뉜다. 이 중 `auth`는 `LOCAL_APPS`에 등록되지 않은,
`models.py` 없이 `services/`(`portal_sso.py`, `ssl_compat.py`)만 갖는 공용 서비스 패키지이며,
같은 네임스페이스의 `sejong.library`/`sejong.student`가 `apps.sejong.auth.services...`를 직접 import해
포털 SSO 인증을 공유한다. model import가 아니라 model이 없는 서비스 전용 패키지의 서비스 import이므로
"앱 간 직접 model import 금지" 규칙 위반이 아니며, `sejong.*` 네임스페이스 내부에서만 허용되는 패턴이다.
다른 도메인 앱이 `apps.sejong.auth`를 import하거나, 이 패턴을 `models.py`가 있는 일반 앱 사이로 확장하지 않는다.

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
#    도메인이 여러 하위 영역으로 나뉘면 apps.sejong.library / apps.sejong.student처럼
#    apps/<domain>/<sub_domain>/ 2단계 네임스페이스도 허용된다(각 하위 패키지를 LOCAL_APPS에 개별 등록).
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

**현재 앱별 URL prefix** (`config/urls.py` 기준):
```
/admin/                          - Django Admin
/media/<path>                    - 업로드 미디어 서빙
/api/v1/health/                  - 헬스체크 (apps.core.urls)
/api/v1/auth/token/              - JWT 발급
/api/v1/auth/token/refresh/      - JWT 갱신
/api/v1/library/                 - 세종대 학술정보원 (apps.sejong.library)
/api/v1/activities/              - GitHub 활동 등 (apps.activity)
/api/v1/blog/                    - 블로그 ingest/카테고리 API (apps.blog)
/api/v1/sejong/students/         - 세종대 학생 조회 (apps.sejong.student)
/api/schema/, /docs/swagger/     - drf-spectacular 스키마/Swagger UI
/accounts/                       - allauth (GitHub 소셜 로그인)
/engagement/                     - 댓글·좋아요 (apps.engagement)
/                                 - SSR 표현 계층 루트 (apps.site, home/blog/projects/lab 등)
```

## Blog Category 계층 제약

- `apps.blog.Category`는 `parent` 자기참조 FK로 대분류/소분류 **2단계까지만** 허용한다.
- `Category.clean()`이 "부모로 지정하려는 카테고리가 이미 누군가의 자식인 경우" `ValidationError`를 발생시켜 3단계 이상 중첩을 막는다.
- Admin에서도 `CategoryAdmin.formfield_for_foreignkey()`가 `parent` 드롭다운을 최상위(`parent__isnull=True`) 카테고리로 제한한다.
- 이 불변조건을 우회하는 방식(예: `parent`를 통해 재귀적으로 트리를 순회하는 로직 추가)은 도입하지 않는다. 3단계 이상이 필요해지면 `clean()`의 깊이 검증 자체를 완화하는 별도 논의를 거친다.
