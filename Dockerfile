# Python 3.12 slim 베이스 이미지 사용
FROM python:3.12-slim

# 기본 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Seoul \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    APP_PORT=8000

# 작업 디렉터리
WORKDIR /app

# 시스템 패키지
# - ca-certificates: https 요청 시 인증서 문제 방지 (httpx 등)
# - nodejs/npm: django-tailwind 빌드에 필요
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      nodejs \
      npm && \
    rm -rf /var/lib/apt/lists/*

# requirements 먼저 복사해 Docker 레이어 캐시 활용
COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r /app/requirements/production.txt

# 애플리케이션 소스 코드 복사
COPY . /app

# Tailwind CSS 프로덕션 빌드 (Node 의존성 설치 포함)
# tailwind install/build는 기본적으로 비대화식으로 동작해 별도 플래그 없이 Docker 빌드에서 그대로 동작한다.
RUN SECRET_KEY=build-time-dummy DATABASE_URL=sqlite:///dummy python manage.py tailwind install && \
    SECRET_KEY=build-time-dummy DATABASE_URL=sqlite:///dummy python manage.py tailwind build

# whitenoise 정적파일 수집 (DB 불필요, 빌드 타임에 처리)
RUN SECRET_KEY=build-time-dummy DATABASE_URL=sqlite:///dummy python manage.py collectstatic --noinput

EXPOSE 8000

# 컨테이너 시작 시 마이그레이션 후 gunicorn 기동
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${APP_PORT} --workers 1"]
