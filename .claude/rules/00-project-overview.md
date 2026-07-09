# Project Overview

## Purpose

- **목적**: 개인 홈서버 백엔드
- **소비자**: 개인 사용 (Baek Jihoon)

## Primary Stack

- Language: Python 3.12
- Framework: Django 5.1 + Django REST Framework 3.15
- Runtime: Gunicorn 22 (production)
- Database / storage: PostgreSQL — `config/settings/base.py`의 `env.db('DATABASE_URL')`로 production/development 공통 설정(환경별 값은 `.env.production`/`.env.local`에서 주입, SQLite 오버라이드 없음)
- Infra / deployment: Docker, GitHub Actions CI/CD (SSH 배포), 서버 포트 8082

## Key Dependencies

```
# requirements/base.txt (공통)
Django==5.1.*
djangorestframework==3.15.*
djangorestframework-simplejwt==5.3.*
drf-spectacular==0.27.*
django-environ==0.11.*
django-cors-headers==4.4.*
whitenoise==6.7.*
psycopg2-binary==2.9.*
gunicorn==22.*
requests==2.32.*
beautifulsoup4==4.12.*
lxml==5.3.*
django-apscheduler==0.7.*   # apps.core 인앱 스케줄러(ScheduledJobConfig)
markdown==3.7.*             # 블로그 포스트 렌더링
bleach==6.4.*                # 마크다운 렌더링 결과 sanitize
django-tailwind==3.8.*       # TAILWIND_APP_NAME='theme', 루트 theme/ 앱
django-allauth==65.3.*       # GitHub 소셜 로그인, SITE_ID=1
Pillow==11.*                 # 이미지 업로드 처리
pillow-heif==1.4.*           # HEIC 이미지 지원

# requirements/development.txt (개발 전용)
pytest==8.3.*
pytest-django==4.9.*
```

## Important directories

`config/settings/base.py`의 `LOCAL_APPS` 등록 순서 기준(실제 앱 목록, 예시가 아님):

```
apps/
  core/               - 헬스체크, apscheduler 기반 인앱 스케줄러(scheduler.py, ScheduledJobConfig)
  notifications/      - 공지·크롤링 알림. crawlers/ 하위에 크롤러 구현체(base/registry/개별 소스별 모듈) 별도 보관
  sejong/
    library/          - 세종대 학술정보원 스터디룸 조회·예약
    student/          - 세종대 학생 조회
    auth/             - LOCAL_APPS 미등록. sejong 하위 앱들이 공유하는 포털 SSO 인증 서비스 전용 패키지(services/만 존재, models 없음)
  activity/           - GitHub 활동 등 수집
  projects/           - 프로젝트 관리
  blog/                - 블로그 (포스트, 카테고리, ingest API)
  accounts/           - 인증/계정 관련
  site/               - SSR 표현 계층 (10-architecture-and-boundaries.md의 SSR 예외 참고)
  engagement/         - 댓글·좋아요 등 참여 기능
  <domain>/           - 신규 기능 단위 앱 (Django app 구조 준수)
    models.py
    views.py / serializers.py
    urls.py
    services/         - 외부 API 연동, 비즈니스 로직
    management/
      commands/       - Django management commands
    tests/
      test_*.py       - pytest-django 테스트
theme/                 - django-tailwind 관례상 루트에 위치, LOCAL_APPS에 'apps.' 접두사 없이 'theme'로 등록되는 유일한 예외
config/
  settings/
    base.py           - 공통 설정 (django-environ 기반, env 파일 로드 안 함)
    development.py    - 개발 설정 (.env.local 로드)
    production.py     - 운영 설정 (.env.production 로드)
  urls.py             - 루트 URL 라우팅
requirements/
  base.txt            - 공통 의존성
  development.txt     - 개발 전용 의존성 (pytest, pytest-django 포함)
  production.txt      - 운영 전용 의존성
pytest.ini             - DJANGO_SETTINGS_MODULE=config.settings.development, testpaths=apps
```

## Main commands

```bash
# 패키지 설치
pip install -r requirements/development.txt

# 개발 서버 실행
python manage.py runserver --settings=config.settings.development

# 마이그레이션
python manage.py migrate --settings=config.settings.development

# 테스트 (pytest.ini가 DJANGO_SETTINGS_MODULE을 development로 고정하므로 --settings 플래그 불필요)
pytest
```

> 테스트·검증 명령을 실제로 실행하는 주체에 대한 규칙은 `30-testing-and-verification.md`를 따른다(에이전트는 안내만 하고 직접 실행하지 않음).

## Project-specific constraints

- 반드시 지켜야 하는 제약:
  - 새 앱 추가 시 `config/settings/base.py`의 `LOCAL_APPS`에 등록 필수
  - 외부 서비스 연동은 `services/` 레이어에만 위치
  - `is_notified` 같은 발송 이력 필드를 활용한 중복 방지 패턴 준수
- 사용 금지:
  - Celery, Redis 등 외부 큐/캐시 (필요 시 논의 후 도입)
  - `print()` — `logging` 또는 `self.stdout.write()` 사용

## Change policy

- 변경 가능: `apps/` 하위 전체, `config/` 설정, `Dockerfile`, CI/CD 워크플로, `requirements/`
- 절대 금지: `.env.*` 파일 수정·커밋, `migrations/` 직접 수정

## Related projects (read-only)

| 프로젝트 | 경로 | 허용 |
|---|---|---|
| chuseok22-home-web (프론트엔드) | `/Users/chuseok22/Workspace/playground/chuseok22-home/chuseok22-home-web` | **Read 전용** — API 스펙 확인·타입 참고 등 필요 시 읽기 허용. **Write/Edit 절대 금지.** |

> 프론트엔드 코드를 참고해야 할 때는 Read 도구로만 접근한다. 어떤 이유로도 해당 경로의 파일을 수정하지 않는다.
