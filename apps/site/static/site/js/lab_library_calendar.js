(function () {
  var DOW = ['일', '월', '화', '수', '목', '금', '토'];
  var today = new Date();
  today.setHours(0, 0, 0, 0);

  var dateInput = document.getElementById('reserve-date-input');
  var triggerLabel = document.getElementById('cal-trigger-label');
  var calendarPop = document.getElementById('calendar-pop');
  var calTrigger = document.getElementById('cal-trigger');

  function parseYyyymmdd(value) {
    return new Date(
      parseInt(value.slice(0, 4), 10),
      parseInt(value.slice(4, 6), 10) - 1,
      parseInt(value.slice(6, 8), 10)
    );
  }

  function formatYyyymmdd(d) {
    return d.getFullYear() +
      String(d.getMonth() + 1).padStart(2, '0') +
      String(d.getDate()).padStart(2, '0');
  }

  var selectedDate = parseYyyymmdd(dateInput.value);
  var calViewYear = selectedDate.getFullYear();
  var calViewMonth = selectedDate.getMonth();

  function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }

  DOW.forEach(function (d) {
    var span = document.createElement('span');
    span.textContent = d;
    document.getElementById('cal-dow-row').appendChild(span);
  });

  function renderCalendar() {
    document.getElementById('cal-month-label').textContent = calViewYear + '년 ' + (calViewMonth + 1) + '월';
    var grid = document.getElementById('cal-grid');
    grid.innerHTML = '';

    var firstDay = new Date(calViewYear, calViewMonth, 1);
    var startOffset = firstDay.getDay();
    var daysInMonth = new Date(calViewYear, calViewMonth + 1, 0).getDate();

    for (var i = 0; i < startOffset; i++) {
      // 'invisible' 같은 새 Tailwind 클래스를 JS로만 만들면 재빌드에도 컴파일되지 않으므로
      // (위 Step 2 주의 참고) 인라인 스타일로 처리한다.
      var filler = document.createElement('button');
      filler.className = 'btn btn-ghost btn-xs';
      filler.style.visibility = 'hidden';
      filler.disabled = true;
      grid.appendChild(filler);
    }
    for (var day = 1; day <= daysInMonth; day++) {
      var d = new Date(calViewYear, calViewMonth, day);
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-xs ' + (sameDay(d, selectedDate) ? 'btn-primary' : 'btn-ghost');
      btn.textContent = day;
      if (d < today) {
        btn.disabled = true;
        btn.style.opacity = '0.35';
      } else {
        btn.addEventListener('click', function (dateVal) {
          return function () {
            selectedDate = dateVal;
            dateInput.value = formatYyyymmdd(dateVal);
            triggerLabel.textContent = dateInput.value;
            calendarPop.classList.add('hidden');
            renderCalendar();
            // 현재 활성화된 룸 종류 탭을 다시 클릭해 htmx로 날짜 변경 반영
            // hx-disabled-elt="this"로 요청 중인 탭은 disabled 상태가 되어 .click()이 동작하지 않으므로
            // htmx.trigger()로 직접 트리거한다.
            var activeTab = document.querySelector('#room-type-tabs .tab-active');
            if (activeTab) htmx.trigger(activeTab, 'click');
          };
        }(d));
      }
      grid.appendChild(btn);
    }
  }

  calTrigger.addEventListener('click', function (e) {
    e.stopPropagation();
    calendarPop.classList.toggle('hidden');
  });
  document.getElementById('cal-prev').addEventListener('click', function () {
    calViewMonth--;
    if (calViewMonth < 0) { calViewMonth = 11; calViewYear--; }
    renderCalendar();
  });
  document.getElementById('cal-next').addEventListener('click', function () {
    calViewMonth++;
    if (calViewMonth > 11) { calViewMonth = 0; calViewYear++; }
    renderCalendar();
  });
  document.addEventListener('click', function (e) {
    if (!calendarPop.contains(e.target) && e.target !== calTrigger && !calTrigger.contains(e.target)) {
      calendarPop.classList.add('hidden');
    }
  });

  document.querySelectorAll('#room-type-tabs .tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      document.querySelectorAll('#room-type-tabs .tab').forEach(function (t) { t.classList.remove('tab-active'); });
      tab.classList.add('tab-active');
    });
  });

  triggerLabel.textContent = dateInput.value;
  renderCalendar();
})();
