# Deployment

## DB 마이그레이션

**Dockerfile `CMD`에 자동 마이그레이션이 설정되어 있다.**

```dockerfile
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn ..."]
```

- 컨테이너 시작 시 migrate → gunicorn 순서로 자동 실행된다.
- 배포 후 수동으로 `migrate`를 실행할 필요 없다.
- 에이전트는 배포 후 migrate 실행을 사용자에게 안내하지 않는다.

## 마이그레이션 파일 생성

모델 변경 시 개발 환경에서 마이그레이션 파일만 생성하면 된다.

```bash
python manage.py makemigrations --settings=config.settings.development
```

생성된 파일을 커밋하면 배포 시 자동으로 적용된다.
