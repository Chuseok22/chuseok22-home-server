# Testing And Verification

## 에이전트 행동 원칙

- **에이전트는 테스트·검증 명령을 직접 실행하지 않는다.**
- 구현 완료 후 사용자에게 실행해야 할 명령을 안내하는 방식으로 검증을 진행한다.
- 서버 배포 후 확인이 필요한 작업도 동일하게 안내만 제공한다.

## Test strategy

- 테스트 프레임워크: pytest + pytest-django (도입 완료). 루트 `pytest.ini`가 `DJANGO_SETTINGS_MODULE=config.settings.development`, `testpaths=apps`로 고정되어 있어 `pytest` 실행 시 `--settings` 플래그가 불필요하다.
- 테스트 코드 위치: 각 앱의 `apps/<domain>/tests/test_*.py` (`.claude/rules/00-project-overview.md`의 "Important directories" 참고)
- 새 기능/버그 수정 시 관련 `tests/test_*.py`에 케이스를 작성하는 것을 기본으로 한다 — 아래 "에이전트 행동 원칙"은 **테스트 코드 작성**이 아니라 **테스트·검증 명령의 실행 주체**에 대한 규칙이다. 즉 에이전트는 `pytest` 등 검증 명령을 직접 실행하지 않고 사용자에게 안내하되, 테스트 코드 자체는 구현의 일부로 작성한다.
- 검증 방식 우선순위: 단위/통합 테스트(pytest) + 실제 동작 확인(management command 직접 실행, 외부 연동 실제 호출)을 함께 사용한다. 외부 API 연동처럼 pytest로 검증하기 어려운 부분은 management command 실행 결과로 보완한다.

## 안내할 검증 명령

에이전트는 아래 명령을 상황에 맞게 사용자에게 안내한다:

```bash
# 전체 테스트 실행 (pytest.ini가 설정을 고정하므로 --settings 불필요)
pytest

# 특정 앱만 실행
pytest apps/<domain>/tests/

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

- `pytest` 실행 결과 (통과/실패 개수)
- management command 실행 결과 (stdout/stderr)
- 외부 연동 수신 확인 (텔레그램 등)

## Failure handling

실패 시 우선 확인할 것을 사용자에게 안내:

1. 컨테이너 로그: `docker logs --tail=200 <container>`
2. Django 설정 오류: `python manage.py check --settings=...`
3. DB 연결 오류: `DATABASE_URL` 환경변수 확인
4. 외부 API 오류: 관련 환경변수 (`TELEGRAM_BOT_TOKEN` 등) 확인
