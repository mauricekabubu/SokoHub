(function () {
  "use strict";

  /* ---------- Mobile drawer ---------- */
  var drawer = document.getElementById("sh-drawer");
  var backdrop = document.getElementById("sh-drawer-backdrop");
  var openBtn = document.getElementById("sh-drawer-open");
  var closeBtn = document.getElementById("sh-drawer-close");

  function openDrawer() {
    if (!drawer) return;
    drawer.classList.add("is-open");
    backdrop.classList.add("is-open");
    openBtn.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }
  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.remove("is-open");
    backdrop.classList.remove("is-open");
    openBtn.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }
  if (openBtn) openBtn.addEventListener("click", openDrawer);
  if (closeBtn) closeBtn.addEventListener("click", closeDrawer);
  if (backdrop) backdrop.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeDrawer();
  });

  /* ---------- Toast ---------- */
  var toastEl = document.getElementById("sh-toast");
  var toastTimer = null;
  function showToast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastEl.classList.remove("is-visible");
    }, 2400);
  }

  /* ---------- Wishlist (visual only, no backend model) ---------- */
  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".sh-wishlist-btn");
    if (!btn) return;
    e.preventDefault();
    btn.classList.toggle("is-active");
    var active = btn.classList.contains("is-active");
    showToast(active ? "Added to wishlist" : "Removed from wishlist");
  });

  /* ---------- Deal-of-the-day countdown ---------- */
  var hoursEl = document.getElementById("sh-cd-hours");
  var minsEl = document.getElementById("sh-cd-mins");
  var secsEl = document.getElementById("sh-cd-secs");

  if (hoursEl && minsEl && secsEl) {
    var totalSeconds =
      parseInt(hoursEl.textContent, 10) * 3600 +
      parseInt(minsEl.textContent, 10) * 60 +
      parseInt(secsEl.textContent, 10);

    setInterval(function () {
      if (totalSeconds <= 0) {
        totalSeconds = 12 * 3600; // reset the demo window once it lapses
      }
      totalSeconds -= 1;
      var h = Math.floor(totalSeconds / 3600);
      var m = Math.floor((totalSeconds % 3600) / 60);
      var s = totalSeconds % 60;
      hoursEl.textContent = String(h).padStart(2, "0");
      minsEl.textContent = String(m).padStart(2, "0");
      secsEl.textContent = String(s).padStart(2, "0");
    }, 1000);
  }
})();