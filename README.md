# chuseok22-home-server

개인 홈서버 백엔드 — 학업 자동화, 생활 알림, 개인 포트폴리오 사이트를 하나의 Django 프로젝트로 운영합니다.

🔗 **https://chuseok22.com**

## 소개

`chuseok22-home-server`는 백지훈(Chuseok22) 개인이 운영하는 모놀리식 Django 백엔드입니다. 세종대학교 학술정보원 스터디룸 예약, 자격증 시험 일정 알림, 관심 영화 예매 오픈 알림 같은 개인 자동화 기능과, 프로필·프로젝트·블로그를 소개하는 SSR 웹사이트를 같은 서버에서 함께 운영합니다.

## 주요 기능

### 포트폴리오 사이트

- 프로필, 경력, 기술 스택, GitHub 활동 통계를 보여주는 홈 화면
- 프로젝트 소개 페이지
- 마크다운 기반 블로그 (브라우저에서 바로 글쓰기·수정·이미지 업로드)
- 게시물 댓글·좋아요

### 자동화 알림

- 학교 공지·공모전 크롤링 후 디스코드/텔레그램 알림
- 자격증 시험 일정 캘린더 조회 + 원서접수 임박 알림
- 관심 영화의 예매 오픈을 감지해 알림 발송
- IT 연합동아리 모집 오픈 감지 알림

### 세종대학교 연동 (Lab)

- 학술정보원 스터디룸 실시간 조회 및 예약
- 재학생 정보 조회

### 맛집 아카이브

- 카카오맵 연동 맛집 등록, 태그 분류, 방문자 제보

### AI 챗봇

- 자체 AI 서버(SUH-AIder) 연동 챗봇, 기능별 프롬프트·모델 관리

## 기술 스택

- **Backend**: Python 3.12, Django 5.1, Django REST Framework
- **Database**: PostgreSQL
- **Infra**: Docker, Gunicorn, WhiteNoise, GitHub Actions CI/CD (SSH 배포)
- **Frontend**: Django Template + django-tailwind (Tailwind CSS)
- **Auth**: djangorestframework-simplejwt, django-allauth (GitHub OAuth)
- **Scheduler**: django-apscheduler 기반 인앱 스케줄러 (Celery·Redis 등 외부 큐 미사용)
- **API 문서**: drf-spectacular (Swagger)

## 프로젝트 구조

```text
apps/
  core/            헬스체크, 인앱 스케줄러
  notifications/   공지·공모전 크롤링 알림
  sejong/          학술정보원 예약(library), 학생 조회(student), 포털 SSO(auth)
  certifications/  자격증 시험 일정 캘린더·알림
  cinema/          영화 예매 오픈 알림
  clubs/           동아리 모집 오픈 감지 알림
  places/          맛집 아카이브
  activity/        GitHub 활동 수집
  projects/        프로젝트 관리
  blog/            블로그
  engagement/      댓글·좋아요
  accounts/        GitHub 소셜 로그인
  profile/         프로필·경력·기술스택
  ai/              AI 연동 인프라
  site/            SSR 웹 프론트엔드
```

각 도메인 앱은 `views → services → models` 구조를 따르며, 외부 API 연동은 `services/` 레이어로 분리되어 있습니다.

## 로컬 실행

```bash
pip install -r requirements/development.txt
python manage.py migrate --settings=config.settings.development
python manage.py runserver --settings=config.settings.development
```

`.env.local`에 `SECRET_KEY`, `DATABASE_URL` 등 필요한 환경변수 설정이 필요합니다.

## API 문서

Swagger UI: `/docs/swagger/`

## 문의

GitHub: [@Chuseok22](https://github.com/Chuseok22)
