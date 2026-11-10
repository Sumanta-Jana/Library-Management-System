/* Woodgrain Library - small helpers (no dependencies) */
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Toasts: close button + auto-dismiss
  $$(".toast").forEach(function (t) {
    function close() { t.style.transition = "opacity .3s, transform .3s"; t.style.opacity = 0; t.style.transform = "translateX(20px)"; setTimeout(function () { t.remove(); }, 300); }
    $(".x", t).addEventListener("click", close);
    setTimeout(close, t.classList.contains("danger") ? 9000 : 6000);
  });

  // Mobile sidebar
  var shell = $("#shell");
  if (shell) {
    var toggle = function () { shell.classList.toggle("open"); };
    var mb = $("#menu-btn"), sc = $("#scrim");
    if (mb) mb.addEventListener("click", toggle);
    if (sc) sc.addEventListener("click", toggle);
  }

  // Show / hide password
  $$("[data-toggle-pw]").forEach(function (b) {
    b.addEventListener("click", function () {
      var input = b.parentElement.querySelector("input");
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      b.textContent = show ? "Hide" : "Show";
    });
  });

  // Confirmation dialog for dangerous forms
  var dlg = $("#confirm-dialog"), pending = null;
  $$("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (f.dataset.ok === "1") return;
      e.preventDefault();
      if (!dlg || !dlg.showModal) { if (confirm(f.dataset.confirm)) { f.dataset.ok = "1"; f.submit(); } return; }
      pending = f; $("#confirm-text").textContent = f.dataset.confirm; dlg.showModal();
    });
  });
  if (dlg) {
    $("#confirm-no").addEventListener("click", function () { dlg.close(); pending = null; });
    $("#confirm-yes").addEventListener("click", function () { dlg.close(); if (pending) { pending.dataset.ok = "1"; pending.submit(); } });
  }

  // Copy buttons
  $$("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var el = $(b.dataset.copy); if (!el) return;
      var text = el.textContent.trim();
      (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(function () {
        b.textContent = "Copied ✓";
      }, function () {
        var r = document.createRange(); r.selectNodeContents(el);
        var s = getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = "Press Ctrl+C";
      });
    });
  });

  // API tester
  var send = $("#t-send");
  if (send) {
    send.addEventListener("click", function () {
      var out = $("#t-out"), key = $("#t-key").value.trim(), path = $("#t-path").value;
      out.textContent = "Loading…";
      fetch(path, { headers: key ? { "X-API-Key": key } : {} })
        .then(function (r) { return r.json().then(function (j) { return { s: r.status, j: j }; }); })
        .then(function (res) { out.textContent = "HTTP " + res.s + "\n" + JSON.stringify(res.j, null, 2); })
        .catch(function (e) { out.textContent = "Request failed: " + e; });
    });
  }

  // Animate bars on load
  $$(".bar").forEach(function (b) { var h = b.style.height; b.style.height = "6px"; setTimeout(function () { b.style.height = h; }, 80); });
})();
