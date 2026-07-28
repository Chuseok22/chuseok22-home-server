# Testing And Verification

## 에이전트 행동 원칙

- **에이전트는 개발 환경(`--settings=config.settings.development`)에서 `pytest`, `python manage.py check`, `python manage.py migrate`(`--check` 포함)를 직접 실행할 수 있다** — 범위를 좁힌 `pytest` 실행(TDD RED→GREEN 등)과 인자 없는 전체 스위트 실행을 모두 포함한다(아래 "에이전트 직접 실행 가능 명령" 참고). 이 명령들 외의 테스트·검증 명령(예: 임의의 다른 management command, 배포 후 확인)은 원칙대로 직접 실행하지 않는다. 예외는 UI 검증을 위한 Playwright 사용(아래 "UI 검증(Playwright)" 참고)뿐이다.
- **운영(prod) 환경에 대해서는 위 허용이 적용되지 않는다.** `--settings=config.settings.production`으로 `migrate`/`check`를 실행하는 것, 운영 DB에 연결된 상태에서의 어떤 검증 명령 실행도 에이전트가 직접 하지 않는다. (참고: 운영 마이그레이션은 `.claude/rules/40-deployment.md`에 따라 컨테이너 시작 시 자동 실행되며, 별도 수동 실행 자체가 필요 없다.)
- 서버 배포 후 확인이 필요한 작업, 위에서 허용한 것 외의 임의의 management command(데이터 시딩·변경 가능성이 있는 커맨드 등)는 여전히 사용자에게 실행해야 할 명령을 안내하는 방식으로 진행한다.

## UI 검증(Playwright)

- `apps.site`(SSR 표현 계층) 등 UI(템플릿·정적 페이지)를 제작·수정할 때는 Playwright를 사용해 실제 렌더링 결과를 직접 확인하는 것을 **허용하고 권장**한다.
- 개발 서버(`python manage.py runserver --settings=config.settings.development`)를 띄운 상태에서 해당 페이지에 접속해 스크린샷, 콘솔 로그, 레이아웃 등을 직접 확인한다.
- 이 예외는 브라우저 기반 UI 확인에 한정되며, 다른 명령 직접 실행 가능 여부와는 별개다.

## 에이전트 직접 실행 가능 명령

모두 **개발 환경(`--settings=config.settings.development`) 한정**이다. 운영(prod) 환경에서는 아래 명령
전부 에이전트가 직접 실행하지 않는다.

- **`pytest`**: 에이전트(또는 서브에이전트)가 직접 실행할 수 있다. 아래 두 경우 모두 포함한다:
  - TDD 방식으로 구현을 진행할 때(예: 계획서의 Task 단위 구현, `superpowers:subagent-driven-development`/`superpowers:test-driven-development` 워크플로) 자신이 작성 중인 범위의 `pytest`로 RED(실패) → GREEN(통과) 전환을 스스로 검증. 예: `pytest apps/<domain>/tests/test_foo.py -v`처럼 해당 Task가 건드리는 테스트 파일/디렉터리로 범위를 좁혀 실행.
  - 구현 완료 후 회귀 확인을 위한 인자 없는 전체 스위트 실행(`pytest`).
- **`python manage.py check --settings=config.settings.development`**: Django 설정 오류 확인용으로 에이전트가 직접 실행할 수 있다.
- **`python manage.py migrate --check --settings=config.settings.development`**: 마이그레이션 적용 여부(드리프트) 확인용으로 에이전트가 직접 실행할 수 있다.
- **`python manage.py migrate --settings=config.settings.development`**: 개발 DB에 실제로 마이그레이션을 적용하는 것도 에이전트가 직접 실행할 수 있다(개발 환경 한정이라 데이터 손실 위험이 낮음).
- 이 허용 범위는 **개발 환경에서의 위 명령들에 한정된다.** 아래는 여전히 사용자에게 안내만 한다:
  - `--settings=config.settings.production`으로 실행하는 모든 명령(운영 마이그레이션은 어차피 배포 시 컨테이너가 자동 실행하므로 수동 실행 자체가 불필요 — `.claude/rules/40-deployment.md` 참고)
  - 위에 나열되지 않은 그 외 임의의 management command(데이터 시딩·변경 등 부작용이 있을 수 있는 커맨드)
  - 서버 배포 후 확인이 필요한 작업

## Test strategy

- 테스트 프레임워크: pytest + pytest-django (도입 완료). 루트 `pytest.ini`가 `DJANGO_SETTINGS_MODULE=config.settings.development`, `testpaths=apps`로 고정되어 있어 `pytest` 실행 시 `--settings` 플래그가 불필요하다.
- 테스트 코드 위치: 각 앱의 `apps/<domain>/tests/test_*.py` (`.claude/rules/00-project-overview.md`의 "Important directories" 참고)
- 새 기능/버그 수정 시 관련 `tests/test_*.py`에 케이스를 작성하는 것을 기본으로 한다 — 위 "에이전트 행동 원칙"은 **테스트 코드 작성**이 아니라 **테스트·검증 명령의 실행 주체**에 대한 규칙이다. 에이전트는 개발 환경의 `pytest`/`check`/`migrate`(`--check` 포함)는 직접 실행하되, 운영 환경 명령이나 그 외 management command, 배포 후 확인은 사용자에게 안내한다.
- 검증 방식 우선순위: 단위/통합 테스트(pytest) + 실제 동작 확인(management command 직접 실행, 외부 연동 실제 호출)을 함께 사용한다. 외부 API 연동처럼 pytest로 검증하기 어려운 부분은 management command 실행 결과로 보완한다.

## 검증 명령

에이전트가 직접 실행할 수 있는 명령(위 "에이전트 직접 실행 가능 명령" 참고):

```bash
# 전체 테스트 실행 (pytest.ini가 설정을 고정하므로 --settings 불필요)
pytest

# 특정 앱만 실행
pytest apps/<domain>/tests/

# Django 설정 오류 확인
python manage.py check --settings=config.settings.development

# 마이그레이션 상태(드리프트) 확인
python manage.py migrate --check --settings=config.settings.development

# 개발 DB에 실제 마이그레이션 적용
python manage.py migrate --settings=config.settings.development
```

아래는 여전히 사용자에게 안내만 하고 에이전트가 직접 실행하지 않는다:

```bash
# 운영(prod) 환경에서의 동일 명령들 — 절대 직접 실행 금지
python manage.py migrate --settings=config.settings.production
python manage.py check --settings=config.settings.production

# management command 실행 (기능 검증, 데이터 변경 가능성 있음)
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
