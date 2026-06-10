# Delivery And Review

## Report format

- report 단계에서 반드시 포함할 섹션:
  - 변경 목적
  - 변경 파일
  - 위험 요소
  - 검증 결과
  - 남은 이슈

- 보고서 파일 저장 위치 및 명명 규칙:
  - 위치: `.report/` 디렉토리 (없으면 자동 생성)
  - 파일명: `[YYYYMMDD]_[간단한설명].md`
  - 예시: `20260611_seed_notices_커맨드_추가.md`

- 보고서 작성 핵심 원칙:
  - **작성자/작성일 필드 절대 포함 금지** — 파일명에 날짜 포함되므로 별도 기록 불필요
  - **AI 도구명 언급 금지** (Claude, GPT, Copilot, Cursor 등)
  - 능동태, 키워드 기반 문장으로 가독성 향상
  - 민감 정보(토큰, 비밀번호, API Key) 발견 시 `{TOKEN}`, `{API_KEY}`, `{PASSWORD}` 형식으로 마스킹

- 보고서 구조:

  ```markdown
  ### 📌 작업 개요
  [2-3줄 요약]

  ### 🎯 구현 목표 (기능 구현) 또는 🔍 문제 분석 (버그 수정)
  [목적 또는 문제 원인]

  ### ✅ 구현 내용

  #### [주요 변경사항 1]
  - **파일**: `경로/파일명`
  - **변경 내용**: [구체적인 설명]
  - **이유**: [왜 이렇게 수정했는지]

  ### 🧪 검증 결과
  [management command 실행 결과, Docker 빌드 결과. PASS/FAIL 명시]

  ### ⚠️ 위험 요소
  [없으면 "없음" 명시]

  ### 📌 남은 이슈
  [후속 작업, 미검증 경로, 서버 배포 후 필요한 추가 작업 등]
  ```

## Pull request expectations

- PR 제목 규칙:
  - 형식: `[타입]: [설명]`
  - 타입: `feat` (기능), `fix` (버그), `refactor`, `chore`, `docs`, `ci`
  - 예시: `feat: 6개 공지 채널 씨딩 커맨드 추가`
  - 현재 프로젝트 커밋 패턴: `git log --oneline` 참고

- PR 본문 구조:
  - 변경 목적, 주요 변경 파일, 검증 결과 포함
  - 배포 후 필요한 추가 작업이 있으면 명시 (예: `seed_notices` 실행 필요)

## Delivery constraints

- 배포 전 확인 사항:
  - `docker build` — 빌드 성공
  - `python manage.py check --settings=config.settings.production` — 설정 오류 없음
  - CI/CD 헬스체크 통과 (`/api/v1/health/` 200 응답)
  - 필요한 환경변수 (`SECRET_KEY`, `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ALLOWED_HOSTS`) 서버 `.env.production`에 설정 확인

- 배포 후 필요한 수동 작업이 있는 경우 PR 본문에 명시:
  - 예: 새 management command 추가 시 서버에서 최초 1회 실행 필요

- rollback 기준:
  - 헬스체크(`/api/v1/health/`) 지속 실패
  - DB 마이그레이션 오류로 서비스 기동 불가
  - rollback 방법: 이전 커밋으로 revert 후 재배포

- feature flag 정책:
  - 현재 미사용. 미완성 기능이 main 브랜치에 포함되어야 하는 경우에만 도입 논의
