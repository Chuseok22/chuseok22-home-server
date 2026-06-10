# Project Overview

## Purpose

- **목적**: 개인 홈서버 백엔드
- **소비자**: 개인 사용 (Baek Jihoon)

## Primary Stack

- Language: Python 3.12
- Framework: Django 5.1 + Django REST Framework 3.15
- Runtime: Gunicorn 22 (production)
- Database / storage: PostgreSQL (production), PostgreSQL (development/test)
- Infra / deployment: Docker, GitHub Actions CI/CD (SSH 배포), 서버 포트 8082

## Key Dependencies

```
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
```

## Important directories

```
apps/
  core/               - 헬스체크 등 인프라성 엔드포인트
  <domain>/           - 기능 단위 앱 (Django app 구조 준수)
    models.py
    views.py / serializers.py
    urls.py
    services/         - 외부 API 연동, 비즈니스 로직
    management/
      commands/       - Django management commands
config/
  settings/
    base.py           - 공통 설정 (django-environ 기반, env 파일 로드 안 함)
    development.py    - 개발 설정 (.env.local 로드)
    production.py     - 운영 설정 (.env.production 로드)
  urls.py             - 루트 URL 라우팅
requirements/
  base.txt            - 공통 의존성
  development.txt     - 개발 전용 의존성
  production.txt      - 운영 전용 의존성
```

## Main commands

```bash
# 패키지 설치
pip install -r requirements/development.txt

# 개발 서버 실행
python manage.py runserver --settings=config.settings.development

# 마이그레이션
python manage.py migrate --settings=config.settings.development
```

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
