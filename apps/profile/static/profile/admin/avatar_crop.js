(function () {
  const MIN_BOX_SIZE = 40; // 미리보기 좌표계 기준 최소 크롭 박스 크기(px)
  const MAX_PREVIEW_WIDTH = 320; // 미리보기 최대 표시 너비(px), 원본 비율은 유지

  function clamp(value, min, max) {
    return Math.max(min, Math.min(value, max));
  }

  document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('id_avatar');
    const cropXInput = document.getElementById('id_avatar_crop_x');
    const cropYInput = document.getElementById('id_avatar_crop_y');
    const cropWidthInput = document.getElementById('id_avatar_crop_width');
    const cropHeightInput = document.getElementById('id_avatar_crop_height');

    if (!fileInput || !cropXInput || !cropYInput || !cropWidthInput || !cropHeightInput) {
      return;
    }

    let cropState = null; // { scale, displayWidth, displayHeight }
    let currentObjectUrl = null; // 파일을 다시 선택할 때 이전 objectURL을 해제하기 위해 보관한다.

    fileInput.addEventListener('change', function () {
      // 미리보기 성공 여부와 무관하게 즉시 이전 크롭 상태를 비운다. HEIC 등 브라우저가
      // <img>로 렌더링하지 못하는 형식을 선택하면 onload가 호출되지 않아, 정리하지 않으면
      // 화면에 이전 파일의 미리보기·좌표가 남은 채 새 파일과 함께 제출될 수 있다.
      cropXInput.value = '';
      cropYInput.value = '';
      cropWidthInput.value = '';
      cropHeightInput.value = '';
      removeExistingUi();

      const file = fileInput.files[0];
      if (!file) {
        return;
      }
      const objectUrl = URL.createObjectURL(file);
      const image = new Image();
      image.onload = function () {
        initCropUi(image, objectUrl);
      };
      image.onerror = function () {
        console.warn('아바타 미리보기를 렌더링할 수 없습니다. 좌표 없이 원본이 업로드되며, 서버에서 중앙 정사각형으로 크롭됩니다.');
        URL.revokeObjectURL(objectUrl);
      };
      image.src = objectUrl;
    });

    function initCropUi(image, objectUrl) {
      removeExistingUi();
      currentObjectUrl = objectUrl;

      const displayWidth = Math.min(image.naturalWidth, MAX_PREVIEW_WIDTH);
      const scale = displayWidth / image.naturalWidth;
      const displayHeight = image.naturalHeight * scale;

      const wrapper = document.createElement('div');
      wrapper.id = 'avatar-crop-wrapper';
      wrapper.style.position = 'relative';
      wrapper.style.width = displayWidth + 'px';
      wrapper.style.height = displayHeight + 'px';
      wrapper.style.marginTop = '8px';
      wrapper.style.touchAction = 'none';

      const previewImage = document.createElement('img');
      previewImage.src = objectUrl;
      previewImage.style.width = '100%';
      previewImage.style.height = '100%';
      previewImage.style.display = 'block';
      previewImage.draggable = false;

      const boxSize = Math.min(displayWidth, displayHeight);
      const box = document.createElement('div');
      box.id = 'avatar-crop-box';
      box.style.position = 'absolute';
      box.style.left = ((displayWidth - boxSize) / 2) + 'px';
      box.style.top = ((displayHeight - boxSize) / 2) + 'px';
      box.style.width = boxSize + 'px';
      box.style.height = boxSize + 'px';
      box.style.border = '2px solid #79aec8';
      box.style.boxSizing = 'border-box';
      box.style.cursor = 'move';

      const handle = document.createElement('div');
      handle.style.position = 'absolute';
      handle.style.right = '-6px';
      handle.style.bottom = '-6px';
      handle.style.width = '12px';
      handle.style.height = '12px';
      handle.style.background = '#79aec8';
      handle.style.cursor = 'nwse-resize';
      box.appendChild(handle);

      wrapper.appendChild(previewImage);
      wrapper.appendChild(box);
      fileInput.parentElement.appendChild(wrapper);

      cropState = { scale: scale, displayWidth: displayWidth, displayHeight: displayHeight };

      enableDrag(box, wrapper);
      enableResize(handle, box, wrapper);
      writeCropInputs(box);
    }

    function removeExistingUi() {
      const existing = document.getElementById('avatar-crop-wrapper');
      if (existing) {
        existing.remove();
      }
      if (currentObjectUrl) {
        URL.revokeObjectURL(currentObjectUrl);
        currentObjectUrl = null;
      }
    }

    function enableDrag(box, wrapper) {
      let dragging = false;
      let startX = 0;
      let startY = 0;
      let boxLeft = 0;
      let boxTop = 0;

      box.addEventListener('pointerdown', function (event) {
        if (event.target !== box) {
          return; // 리사이즈 핸들 클릭은 enableResize가 처리한다.
        }
        dragging = true;
        startX = event.clientX;
        startY = event.clientY;
        boxLeft = parseFloat(box.style.left);
        boxTop = parseFloat(box.style.top);
        box.setPointerCapture(event.pointerId);
      });

      box.addEventListener('pointermove', function (event) {
        if (!dragging) {
          return;
        }
        const size = parseFloat(box.style.width);
        const maxLeft = wrapper.clientWidth - size;
        const maxTop = wrapper.clientHeight - size;
        box.style.left = clamp(boxLeft + (event.clientX - startX), 0, maxLeft) + 'px';
        box.style.top = clamp(boxTop + (event.clientY - startY), 0, maxTop) + 'px';
        writeCropInputs(box);
      });

      box.addEventListener('pointerup', function () {
        dragging = false;
      });
    }

    function enableResize(handle, box, wrapper) {
      let resizing = false;
      let startX = 0;
      let startSize = 0;

      handle.addEventListener('pointerdown', function (event) {
        resizing = true;
        startX = event.clientX;
        startSize = parseFloat(box.style.width);
        handle.setPointerCapture(event.pointerId);
        event.stopPropagation();
      });

      handle.addEventListener('pointermove', function (event) {
        if (!resizing) {
          return;
        }
        const left = parseFloat(box.style.left);
        const top = parseFloat(box.style.top);
        const maxSize = Math.min(wrapper.clientWidth - left, wrapper.clientHeight - top);
        // maxSize가 MIN_BOX_SIZE보다 작아지는 경우(매우 가로/세로로 긴 이미지) clamp(min, max)의
        // min이 max보다 커지면 항상 min을 반환해 박스가 이미지 경계 밖으로 나갈 수 있다.
        // 하한을 maxSize를 넘지 않게 미리 보정해 결과가 항상 maxSize 이하가 되도록 한다.
        const lowerBound = Math.min(MIN_BOX_SIZE, maxSize);
        const nextSize = clamp(startSize + (event.clientX - startX), lowerBound, maxSize);
        box.style.width = nextSize + 'px';
        box.style.height = nextSize + 'px';
        writeCropInputs(box);
      });

      handle.addEventListener('pointerup', function () {
        resizing = false;
      });
    }

    function writeCropInputs(box) {
      const scale = cropState.scale;
      const left = parseFloat(box.style.left);
      const top = parseFloat(box.style.top);
      const size = parseFloat(box.style.width);

      cropXInput.value = Math.round(left / scale);
      cropYInput.value = Math.round(top / scale);
      cropWidthInput.value = Math.round(size / scale);
      cropHeightInput.value = Math.round(size / scale);
    }
  });
})();
