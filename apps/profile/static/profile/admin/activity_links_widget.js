(function () {
  // 타입→한글 라벨은 apps/site/templatetags/profile_tags.py의 _ACTIVITY_LINK_ICONS,
  // apps/profile/models.py의 _ACTIVITY_LINK_TYPES와 동일한 값을 독립적으로 유지한다
  // (site → profile 계층 규칙 때문에 두 앱이 이미 별도 사본을 갖고 있고, 정적 자산인
  // 이 JS는 Python을 import할 수 없어 세 번째 사본이 된다). 타입을 추가/변경하면 이
  // 목록도 함께 갱신해야 한다.
  const LINK_TYPES = [
    { value: 'official', label: '공식 페이지' },
    { value: 'github', label: 'GitHub' },
    { value: 'youtube', label: 'YouTube' },
    { value: 'instagram', label: 'Instagram' },
    { value: 'linkedin', label: 'LinkedIn' },
    { value: 'presentation', label: '발표자료' },
    { value: 'article', label: '관련기사' },
    { value: 'other', label: '링크' },
  ];
  const LINK_TYPE_VALUES = LINK_TYPES.map((type) => type.value);

  function isValidLinkItem(item) {
    return (
      item !== null &&
      typeof item === 'object' &&
      !Array.isArray(item) &&
      typeof item.url === 'string' &&
      LINK_TYPE_VALUES.includes(item.type)
    );
  }

  document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.getElementById('id_links');
    if (!textarea) {
      return;
    }

    let initialLinks;
    try {
      initialLinks = JSON.parse(textarea.value || '[]');
      if (!Array.isArray(initialLinks) || !initialLinks.every(isValidLinkItem)) {
        throw new Error('links 구조가 올바르지 않습니다.');
      }
    } catch (error) {
      // 파싱 실패이거나 항목 구조(type/url)가 예상과 다르면 원본 textarea를 그대로 두고
      // 구조화 UI를 만들지 않는다 (자동 폴백) — 손상된 데이터를 조용히 재작성하지 않기 위함.
      return;
    }

    const rowsContainer = document.createElement('div');
    rowsContainer.className = 'activity-links-rows';

    function syncTextarea() {
      const links = Array.from(rowsContainer.children).map((row) => ({
        type: row.querySelector('.activity-links-type').value,
        url: row.querySelector('.activity-links-url').value,
      }));
      textarea.value = JSON.stringify(links);
    }

    function updateRowStates() {
      const rows = rowsContainer.children;
      Array.from(rows).forEach((row, index) => {
        row.querySelector('.activity-links-move-up').disabled = index === 0;
        row.querySelector('.activity-links-move-down').disabled = index === rows.length - 1;
      });
    }

    function handleChange() {
      updateRowStates();
      syncTextarea();
    }

    function createRow(link) {
      const row = document.createElement('div');
      row.className = 'activity-links-row';

      const select = document.createElement('select');
      select.className = 'activity-links-type';
      select.setAttribute('aria-label', '링크 타입');
      LINK_TYPES.forEach((type) => {
        const option = document.createElement('option');
        option.value = type.value;
        option.textContent = type.label;
        if (type.value === link.type) {
          option.selected = true;
        }
        select.appendChild(option);
      });
      select.addEventListener('change', handleChange);

      const urlInput = document.createElement('input');
      urlInput.type = 'url';
      urlInput.required = true;
      urlInput.placeholder = 'https://...';
      urlInput.className = 'activity-links-url';
      urlInput.value = link.url;
      urlInput.addEventListener('input', handleChange);

      const upButton = document.createElement('button');
      upButton.type = 'button';
      upButton.className = 'activity-links-move-up';
      upButton.textContent = '↑';
      upButton.setAttribute('aria-label', '위로 이동');
      upButton.addEventListener('click', () => {
        const index = Array.prototype.indexOf.call(rowsContainer.children, row);
        if (index > 0) {
          rowsContainer.insertBefore(row, rowsContainer.children[index - 1]);
          handleChange();
        }
      });

      const downButton = document.createElement('button');
      downButton.type = 'button';
      downButton.className = 'activity-links-move-down';
      downButton.textContent = '↓';
      downButton.setAttribute('aria-label', '아래로 이동');
      downButton.addEventListener('click', () => {
        const index = Array.prototype.indexOf.call(rowsContainer.children, row);
        if (index < rowsContainer.children.length - 1) {
          rowsContainer.insertBefore(rowsContainer.children[index + 1], row);
          handleChange();
        }
      });

      const deleteButton = document.createElement('button');
      deleteButton.type = 'button';
      deleteButton.className = 'activity-links-delete';
      deleteButton.textContent = '×';
      deleteButton.setAttribute('aria-label', '링크 삭제');
      deleteButton.addEventListener('click', () => {
        row.remove();
        handleChange();
      });

      row.appendChild(select);
      row.appendChild(urlInput);
      row.appendChild(upButton);
      row.appendChild(downButton);
      row.appendChild(deleteButton);
      return row;
    }

    initialLinks.forEach((link) => {
      rowsContainer.appendChild(createRow(link));
    });

    const addButton = document.createElement('button');
    addButton.type = 'button';
    addButton.className = 'activity-links-add';
    addButton.textContent = '+ 링크 추가';
    addButton.addEventListener('click', () => {
      rowsContainer.appendChild(createRow({ type: 'official', url: '' }));
      handleChange();
    });

    const wrapper = document.createElement('div');
    wrapper.className = 'activity-links-widget';
    wrapper.appendChild(rowsContainer);
    wrapper.appendChild(addButton);

    // textarea 바로 다음 형제(Django admin이 help_text를 렌더링하는 .help 요소)를 위젯
    // 삽입 전에 미리 잡아둔다 — 구조화 UI 옆에 "JSON을 직접 입력하라"는 안내가 남지
    // 않도록 함께 숨긴다. 폼 제출 값(원본 textarea)은 그대로 두므로 안전.
    const helpElement = textarea.nextElementSibling;

    textarea.style.display = 'none';
    textarea.insertAdjacentElement('afterend', wrapper);
    if (helpElement && helpElement.classList.contains('help')) {
      helpElement.style.display = 'none';
    }

    // 초기 렌더링 시점에는 행 활성/비활성 상태만 맞추고, textarea 값은 재직렬화하지
    // 않는다 — 사용자가 아무것도 건드리지 않았는데 저장된 원본 JSON이 바뀌는 것을
    // 막기 위함(예: 검증기가 막지 않는 부가 키가 있는 데이터라도 그대로 보존).
    updateRowStates();
  });
})();
