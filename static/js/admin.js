(function () {
  "use strict";

  document.querySelectorAll("[data-confirm]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      var message = btn.getAttribute("data-confirm");
      if (message && !window.confirm(message)) {
        e.preventDefault();
      }
      // If confirmed (or no message set), the form submits normally —
      // this never intercepts or replaces the real POST request.
    });
  });
})();