# Icon Usage

## 원칙

1. **아이콘을 직접 SVG path로 그려서 임의로 사용하지 않는다.** 브랜드 로고든 UI 아이콘이든 손으로
   좌표를 그려 넣은 `<path d="...">`는 실제 디자인과 미묘하게 달라 깨져 보이는 문제를 일으킨다.
2. **아이콘이 필요하면 라이브러리를 최우선으로 사용한다.**
   - UI/일반 아이콘 → Heroicons(`heroicons` 패키지, `{% heroicon_outline %}` / `{% heroicon_solid %}`
     템플릿 태그).
   - 브랜드/로고 아이콘 → Simple Icons(벤더링된 `apps/core/static/core/icons/simple-icons/`,
     `{% brand_icon %}` 템플릿 태그로 렌더링).
   - 두 라이브러리 어디에도 없는 아이콘이 필요하면 임의로 대체하거나 직접 그리지 말고, 반드시
     사용자에게 확인한 뒤 진행한다.
3. **아이콘은 자체호스팅한다.** 외부 CDN(`cdn.simpleicons.org` 등)을 실시간으로 직접 참조하지
   않는다. Simple Icons에 없는 브랜드는 해당 SVG를 1회성으로 받아
   `apps/core/static/core/icons/other-brands/`에 벤더링하고, DB에는 항상 로컬에서 검증 가능한
   슬러그만 저장한다(CDN 전체 URL을 데이터로 저장하지 않는다).

## 검증 장치

- `apps/profile/models.py`의 `Skill.clean()`은 `icon_slug`가 새로 생성되거나 실제로 바뀌는
  시점(생성 시 스냅샷과 비교)에만 검증한다. 이 dirty-tracking 게이트는 `save()`가 아니라
  `clean()` 안에 둔다 — `save()`는 항상 `full_clean()`을 호출하므로, Django ModelForm이
  `full_clean()`/`clean()`을 `save()`를 거치지 않고 직접 호출하는 경로(예: Admin
  `list_editable` changelist 편집)에서도 게이트가 동일하게 적용된다. `clean()`에만 게이트를
  두면 셸/management command처럼 `save()`를 통하는 경로도, ModelForm처럼 `save()`를
  우회하는 경로도 모두 안전하다.
- `apps/site/tests/test_icon_tags.py`의 아이콘 무결성 테스트가 벤더링된 파일과 실제 참조 사이의
  불일치를 자동으로 잡아낸다. 새 아이콘을 추가하면 관련 테스트도 함께 갱신한다.
