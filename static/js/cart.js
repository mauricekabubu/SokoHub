(function () {
  "use strict";

  /* ---------- CSRF helper ---------- */
  function getCookie(name) {
    var value = "; " + document.cookie;
    var parts = value.split("; " + name + "=");
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
  }
  var csrftoken = getCookie("csrftoken");

  /* ---------- Toast (persists across the reload the backend still needs) ---------- */
  var toastEl = document.getElementById("sh-toast");
  var toastTimer = null;
  function showToast(message) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastEl.classList.remove("is-visible");
    }, 2600);
  }
  function showToastAfterReload(message) {
    try { sessionStorage.setItem("sh_pending_toast", message); } catch (e) { /* storage unavailable */ }
  }
  (function showPendingToastIfAny() {
    try {
      var pending = sessionStorage.getItem("sh_pending_toast");
      if (pending) {
        sessionStorage.removeItem("sh_pending_toast");
        showToast(pending);
      }
    } catch (e) { /* storage unavailable */ }
  })();

  /* ---------- Per-item quantity steppers ---------- */
  document.querySelectorAll(".sh-cart-item").forEach(function (item) {
    var input = item.querySelector('input[id^="select"]');
    if (!input) return;

    function clamp() {
      var val = parseInt(input.value, 10);
      if (isNaN(val) || val < 1) val = 1;
      input.value = val;
    }
    clamp();

    var decBtn = item.querySelector(".sh-qty-decrease");
    var incBtn = item.querySelector(".sh-qty-increase");
    if (decBtn) decBtn.addEventListener("click", function () {
      clamp();
      input.value = Math.max(1, parseInt(input.value, 10) - 1);
    });
    if (incBtn) incBtn.addEventListener("click", function () {
      clamp();
      input.value = parseInt(input.value, 10) + 1;
    });
    input.addEventListener("change", clamp);
  });

  /* ---------- Update cart item (same endpoint + payload as before) ---------- */
  $(".update-cart").on("click", function (e) {
    e.preventDefault();
    var btn = $(this);
    if (btn.hasClass("is-loading")) return;

    var productid = btn.data("index");
    var qtyInput = document.getElementById("select" + productid);
    var qtyVal = qtyInput ? qtyInput.value : 1;

    var originalText = btn.text();
    btn.addClass("is-loading").text("Updating...");

    $.ajax({
      type: "POST",
      url: window.SOKOHUB_CART_UPDATE_URL,
      data: {
        product_id: productid,
        product_qty: qtyVal,
        csrfmiddlewaretoken: csrftoken
      },
      success: function (json) {
        showToastAfterReload("✓ Cart updated successfully");
        location.reload();
      },
      error: function (xhr) {
        console.log("ERROR", xhr.responseText);
        showToast("Something went wrong. Please try again.");
        btn.removeClass("is-loading").text(originalText);
      }
    });
  });

  /* ---------- Delete cart item (same endpoint + payload as before) ---------- */
  $(".delete-product").on("click", function (e) {
    e.preventDefault();
    var btn = $(this);
    if (btn.hasClass("is-loading")) return;

    var productid = btn.data("index");
    var row = btn.closest(".sh-cart-item")[0];

    btn.addClass("is-loading").find("span").text("Removing...");

    $.ajax({
      type: "POST",
      url: window.SOKOHUB_CART_DELETE_URL,
      data: {
        product_id: productid,
        csrfmiddlewaretoken: csrftoken
      },
      success: function (json) {
        showToastAfterReload("✓ Product removed from your cart");
        if (row) {
          row.classList.add("is-removing");
          setTimeout(function () { location.reload(); }, 260);
        } else {
          location.reload();
        }
      },
      error: function (xhr) {
        console.log("ERROR", xhr.responseText);
        showToast("Something went wrong. Please try again.");
        btn.removeClass("is-loading").find("span").text("Remove");
      }
    });
  });
})();