(function () {
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  function insertAtCursor(textarea, text) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = textarea.value.slice(0, start);
    const after = textarea.value.slice(end);
    textarea.value = `${before}${text}${after}`;
    const cursorPosition = start + text.length;
    textarea.setSelectionRange(cursorPosition, cursorPosition);
    textarea.focus();
  }

  document.addEventListener('DOMContentLoaded', function () {
    const textarea = document.getElementById('id_content');
    if (!textarea) {
      return;
    }

    // 현재 페이지가 .../<id>/change/ 또는 .../add/ 이므로, 업로드 엔드포인트는
    // 같은 ModelAdmin 하위의 형제 경로(.../upload-media/)로 계산한다.
    // "change" 앞의 object id(숫자)까지 함께 제거해야 한다 — id를 남겨두면
    // Django admin의 레거시 경로(<path:object_id>/)에 잘못 매칭되어 리다이렉트가 발생한다.
    const uploadUrl = window.location.pathname.replace(/\/(?:\d+\/change|add)\/?$/, '/upload-media/');

    const uploadButton = document.createElement('button');
    uploadButton.type = 'button';
    uploadButton.textContent = '이미지·미디어 업로드';
    uploadButton.style.marginBottom = '8px';

    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.style.display = 'none';

    uploadButton.addEventListener('click', function () {
      fileInput.click();
    });

    fileInput.addEventListener('change', function () {
      const file = fileInput.files[0];
      if (!file) {
        return;
      }

      const formData = new FormData();
      formData.append('file', file);

      const spinner = document.createElement('span');
      spinner.className = 'admin-loading-spinner';

      uploadButton.disabled = true;
      uploadButton.textContent = '업로드 중...';
      uploadButton.appendChild(spinner);

      fetch(uploadUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() },
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            insertAtCursor(textarea, data.markdown);
          } else {
            alert(data.error_message || '업로드에 실패했습니다.');
          }
        })
        .catch(() => {
          alert('업로드 중 오류가 발생했습니다.');
        })
        .finally(() => {
          uploadButton.disabled = false;
          uploadButton.textContent = '이미지·미디어 업로드';
          fileInput.value = '';
        });
    });

    textarea.parentElement.insertBefore(uploadButton, textarea);
    textarea.parentElement.insertBefore(fileInput, textarea);
  });
})();
