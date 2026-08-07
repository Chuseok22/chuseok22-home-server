(function () {
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  function flattenErrors(errors) {
    return Object.values(errors)
      .flat()
      .map((error) => (error && error.message) || String(error));
  }

  function init() {
    const form = document.getElementById('post-edit-form');
    const readView = document.getElementById('post-read-view');
    const toggleButton = document.getElementById('post-edit-toggle');
    if (!form || !readView || !toggleButton) {
      return;
    }

    const titleInput = document.getElementById('post-edit-title');
    const summaryInput = document.getElementById('post-edit-summary');
    const contentTextarea = document.getElementById('post-edit-content');
    const saveButton = document.getElementById('post-edit-save');
    const cancelButton = document.getElementById('post-edit-cancel');
    const errorBox = document.getElementById('post-edit-errors');
    const editUrl = form.dataset.editUrl;
    const uploadUrl = form.dataset.uploadUrl;

    let easyMDE = null;

    function ensureEditor() {
      if (easyMDE) {
        // display:none 상태를 거친 CodeMirror는 재표시 시 치수 계산이 깨져 클릭
        // 전까지 내용이 안 보이는 경우가 있어, 다시 열 때마다 강제로 리렌더링한다.
        easyMDE.codemirror.refresh();
        return;
      }
      if (typeof EasyMDE === 'undefined') {
        return;
      }
      easyMDE = new EasyMDE({
        element: contentTextarea,
        spellChecker: false,
        toolbar: ['upload-image'],
        uploadImage: true,
        imageUploadFunction: function (file, onSuccess, onError) {
          if (!file.type.startsWith('image/')) {
            onError('이미지 파일만 업로드할 수 있습니다.');
            return;
          }

          const formData = new FormData();
          formData.append('file', file);

          fetch(uploadUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
          })
            .then((response) => response.json())
            .then((data) => {
              if (!data.success) {
                onError(data.error_message || '업로드에 실패했습니다.');
                return;
              }
              // EasyMDE의 imageUploadFunction 계약상 onSuccess는 URL 문자열로 호출해야
              // 하며, 그러면 내부적으로 고정 템플릿(![](#url#))이 커서 위치에 삽입된다.
              // 서버가 만들어준 alt 텍스트(data.markdown, 예: ![업로드 이미지](url))를
              // 쓰려면 삽입 직후 그 범위를 우리가 원하는 문자열로 덮어써야 한다
              // (Admin의 post_markdown_editor.js와 동일한 패턴).
              const from = easyMDE.codemirror.getCursor('from');
              onSuccess(data.url);
              const to = easyMDE.codemirror.getCursor();
              easyMDE.codemirror.replaceRange(data.markdown, from, to);
            })
            .catch(() => onError('업로드 중 오류가 발생했습니다.'));
        },
      });
    }

    function showEditMode() {
      readView.classList.add('hidden');
      form.classList.remove('hidden');
      ensureEditor();
    }

    function showReadMode() {
      form.classList.add('hidden');
      readView.classList.remove('hidden');
      errorBox.classList.add('hidden');
      titleInput.value = titleInput.defaultValue;
      summaryInput.value = summaryInput.defaultValue;
      if (easyMDE) {
        easyMDE.value(contentTextarea.defaultValue);
      }
    }

    function displayErrors(errors) {
      errorBox.textContent = flattenErrors(errors).join(' ');
      errorBox.classList.remove('hidden');
    }

    // #post-edit-form은 submit 버튼이 없어도(전부 type="button") 제목/요약 input에서
    // Enter를 누르면 브라우저가 암묵적으로 폼을 제출한다(action 미지정 시 현재 URL로 GET
    // 네비게이션 → 페이지 이동으로 작성 중이던 본문이 전부 사라짐). 반드시 막는다.
    form.addEventListener('submit', function (event) {
      event.preventDefault();
    });

    toggleButton.addEventListener('click', showEditMode);
    cancelButton.addEventListener('click', showReadMode);

    saveButton.addEventListener('click', function () {
      const body = new URLSearchParams({
        title: titleInput.value,
        summary: summaryInput.value,
        content: easyMDE ? easyMDE.value() : contentTextarea.value,
      });

      fetch(editUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: body.toString(),
      })
        .then((response) => response.json().then((data) => ({ status: response.status, data })))
        .then(({ status, data }) => {
          if (status === 200 && data.success) {
            window.location.reload();
            return;
          }
          displayErrors(data.errors || {});
        })
        .catch(() => displayErrors({ network: ['저장 중 오류가 발생했습니다.'] }));
    });
  }

  init();
})();
