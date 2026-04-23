/* WasteLoop — lightweight UX enhancements (no frameworks) */
'use strict';

document.addEventListener('DOMContentLoaded', function () {

  // ── 1. Auto-dismiss flash messages after 4 s ──────────────
  document.querySelectorAll('.alert.alert-dismissible').forEach(function (el) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    }, 4000);
  });

  // ── 2. Confirm before marking paid ───────────────────────
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(form.dataset.confirm)) {
        e.preventDefault();
      }
    });
  });

  // ── 3. Disable submit button after first click ────────────
  //    Prevents double-submission on slow connections
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('button[type="submit"]');
      if (btn && !btn.dataset.noDisable) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Saving…';
      }
    });
  });

  // ── 4. Set today as default date on waste entry form ─────
  var dateInput = document.querySelector('input[type="date"][name="date_collected"]');
  if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().split('T')[0];
  }

  // ── 5. Animate stat card numbers (count-up) ──────────────
  document.querySelectorAll('.stat-value[data-target], .wl-impact-number[data-target]').forEach(function (el) {
    var target = parseFloat(el.dataset.target) || 0;
    var prefix = el.dataset.prefix || '';
    var suffix = el.dataset.suffix || '';
    var duration = 1200;
    var start = performance.now();

    function step(now) {
      var elapsed = now - start;
      var progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = Math.round(eased * target);
      el.textContent = prefix + current.toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });

});
