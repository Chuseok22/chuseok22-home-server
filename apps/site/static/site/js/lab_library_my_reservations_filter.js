(function () {
  var tabs = document.querySelectorAll('#my-reservation-filter .tab');
  var cards = document.querySelectorAll('#my-reservation-list [data-status]');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('tab-active'); });
      tab.classList.add('tab-active');
      var filter = tab.dataset.filter;
      cards.forEach(function (card) {
        card.style.display = (filter === 'all' || card.dataset.status === filter) ? '' : 'none';
      });
    });
  });
})();
