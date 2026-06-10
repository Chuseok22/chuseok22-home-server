# Testing And Verification

## 에이전트 행동 원칙

- **에이전트는 테스트·검증 명령을 직접 실행하지 않는다.**
- 구현 완료 후 사용자에게 실행해야 할 명령을 안내하는 방식으로 검증을 진행한다.
- 서버 배포 후 확인이 필요한 작업도 동일하게 안내만 제공한다.

## Test strategy

- 현재 테스트 프레임워크: 미도입 (pytest + Django test 도입 예정)
- 현재 검증 방식: management command 직접 실행, 외부 연동 실제 호출
- 우선순위: 실제 동작 확인 (외부 API 포함) > 단위 테스트

## 안내할 검증 명령

에이전트는 아래 명령을 상황에 맞게 사용자에게 안내한다:

```bash
# Django 설정 오류 확인
python manage.py check --settings=config.settings.development

# 마이그레이션 상태 확인
python manage.py migrate --check --settings=config.settings.development

# management command 실행 (기능 검증)
python manage.py <command_name> --settings=config.settings.development

# 헬스체크 확인 (서버 기동 후)
curl http://127.0.0.1:8000/api/v1/health/
```

## Evidence

- management command 실행 결과 (stdout/stderr)
- 외부 연동 수신 확인 (텔레그램 등)

## Failure handling

실패 시 우선 확인할 것을 사용자에게 안내:

1. 컨테이너 로그: `docker logs --tail=200 <container>`
2. Django 설정 오류: `python manage.py check --settings=...`
3. DB 연결 오류: `DATABASE_URL` 환경변수 확인
4. 외부 API 오류: 관련 환경변수 (`TELEGRAM_BOT_TOKEN` 등) 확인
