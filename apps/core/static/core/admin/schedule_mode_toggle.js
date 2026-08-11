(function () {
  function toggleFieldsets() {
    const modeInputs = document.querySelectorAll('input[name="schedule_mode"]');
    let selectedMode = 'fixed_times';
    modeInputs.forEach(function (input) {
      if (input.checked) {
        selectedMode = input.value;
      }
    });

    const intervalRow = document.querySelector('.field-interval_hours');
    const intervalMinuteRow = document.querySelector('.field-interval_minute');
    const intervalMinutesRow = document.querySelector('.field-interval_minutes');
    const fixedHourRow = document.querySelector('.field-fixed_hour_list');
    const fixedMinuteRow = document.querySelector('.field-fixed_minute');

    const showInterval = selectedMode === 'interval';
    const showIntervalMinutes = selectedMode === 'interval_minutes';
    const showFixed = selectedMode === 'fixed_times';

    [intervalRow, intervalMinuteRow].forEach(function (row) {
      if (row) {
        row.style.display = showInterval ? '' : 'none';
      }
    });
    [intervalMinutesRow].forEach(function (row) {
      if (row) {
        row.style.display = showIntervalMinutes ? '' : 'none';
      }
    });
    [fixedHourRow, fixedMinuteRow].forEach(function (row) {
      if (row) {
        row.style.display = showFixed ? '' : 'none';
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const modeInputs = document.querySelectorAll('input[name="schedule_mode"]');
    if (!modeInputs.length) {
      return;
    }
    modeInputs.forEach(function (input) {
      input.addEventListener('change', toggleFieldsets);
    });
    toggleFieldsets();
  });
})();
