(function () {
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  function fillFields(result) {
    document.getElementById('id_name').value = result.name;
    document.getElementById('id_address').value = result.address;
    document.getElementById('id_road_address').value = result.road_address;
    document.getElementById('id_latitude').value = result.latitude;
    document.getElementById('id_longitude').value = result.longitude;
    document.getElementById('id_kakao_category').value = result.category;
    document.getElementById('id_kakao_place_url').value = result.place_url;
  }

  document.addEventListener('DOMContentLoaded', function () {
    const nameField = document.getElementById('id_name');
    if (!nameField) {
      return;
    }

    // 현재 페이지가 .../<id>/change/ 또는 .../add/ 이므로, 검색 엔드포인트는
    // 같은 ModelAdmin 하위의 형제 경로(.../kakao-search/)로 계산한다.
    const searchUrl = window.location.pathname.replace(/\/(?:\d+\/change|add)\/?$/, '/kakao-search/');

    const searchButton = document.createElement('button');
    searchButton.type = 'button';
    searchButton.textContent = '카카오맵 검색';
    searchButton.style.marginLeft = '8px';

    const resultsList = document.createElement('ul');
    resultsList.style.marginTop = '8px';
    resultsList.style.listStyle = 'none';
    resultsList.style.padding = '0';

    searchButton.addEventListener('click', function () {
      const query = nameField.value.trim();
      if (!query) {
        alert('검색할 상호명을 입력해주세요.');
        return;
      }

      resultsList.innerHTML = '<li>검색 중...</li>';

      fetch(searchUrl + '?query=' + encodeURIComponent(query), {
        headers: { 'X-CSRFToken': getCsrfToken() },
      })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          resultsList.innerHTML = '';
          if (!data.success) {
            const errorItem = document.createElement('li');
            errorItem.textContent = data.error_message || '검색에 실패했습니다.';
            resultsList.appendChild(errorItem);
            return;
          }
          if (data.results.length === 0) {
            resultsList.innerHTML = '<li>검색 결과가 없습니다.</li>';
            return;
          }
          data.results.forEach(function (result) {
            const item = document.createElement('li');
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = result.name + ' (' + (result.road_address || result.address) + ')';
            button.addEventListener('click', function () {
              fillFields(result);
              resultsList.innerHTML = '';
            });
            item.appendChild(button);
            resultsList.appendChild(item);
          });
        })
        .catch(function () {
          resultsList.innerHTML = '<li>검색 중 오류가 발생했습니다.</li>';
        });
    });

    nameField.parentElement.appendChild(searchButton);
    nameField.parentElement.appendChild(resultsList);
  });
})();
