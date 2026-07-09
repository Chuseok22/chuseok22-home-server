# chuseok22-home-server

개인 홈서버. Django 5.1 + DRF 기반의 백엔드 서버.

## Stack

- Python 3.12 / Django 5.1 / Django REST Framework
- PostgreSQL — `DATABASE_URL` 환경변수 기반(`django-environ`)으로 production/development 공통 설정, 별도 SQLite 오버라이드 없음
- Gunicorn + WhiteNoise
- Docker + GitHub Actions CI/CD
- pytest + pytest-django (테스트), django-allauth(GitHub 소셜 로그인), django-tailwind, django-apscheduler(인앱 스케줄러)

## 핵심 규칙

1. 새 앱은 `apps/<domain>/` 하위에 생성하고 `config/settings/base.py`의 `LOCAL_APPS`에 등록한다.
2. 외부 서비스 연동은 반드시 `apps/<domain>/services/` 하위에 분리한다.
3. `.env.local` (개발) / `.env.production` (운영) — 절대 커밋 금지.
4. 로컬 검증은 `--settings=config.settings.development` 플래그를 사용한다.

## 관련 프로젝트

| 프로젝트 | 경로 | 권한 |
|---|---|---|
| 프론트엔드 (chuseok22-home-web) | `/Users/chuseok22/Workspace/playground/chuseok22-home/chuseok22-home-web` | **읽기 전용** — API 연동·타입 참고 시 Read 가능. **쓰기 절대 금지.** |

## 주요 명령

```bash
# 개발 서버
python manage.py runserver --settings=config.settings.development

# 마이그레이션
python manage.py migrate --settings=config.settings.development
```

## 상세 규칙

자세한 내용은 `.claude/rules/` 를 참고한다.
