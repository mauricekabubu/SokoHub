(function () {
  "use strict";

  /* ---------- CSRF helper (keeps this file static, no inline template code) ---------- */
  function getCookie(name) {
    var value = "; " + document.cookie;
    var parts = value.split("; " + name + "=");
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
  }
  var csrftoken = getCookie("csrftoken");

  /* ---------- Quantity stepper ---------- */
  var qtyInput = document.getElementById("qty-cart");
  var decBtn = document.getElementById("qty-decrease");
  var incBtn = document.getElementById("qty-increase");

  function clampQty() {
    if (!qtyInput) return;
    var val = parseInt(qtyInput.value, 10);
    if (isNaN(val) || val < 1) val = 1;
    qtyInput.value = val;
  }
  if (decBtn) {
    decBtn.addEventListener("click", function () {
      clampQty();
      qtyInput.value = Math.max(1, parseInt(qtyInput.value, 10) - 1);
    });
  }
  if (incBtn) {
    incBtn.addEventListener("click", function () {
      clampQty();
      qtyInput.value = parseInt(qtyInput.value, 10) + 1;
    });
  }
  if (qtyInput) qtyInput.addEventListener("change", clampQty);

  /* ---------- Toast (falls back to no-op if shop.js hasn't set one up) ---------- */
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

  /* ---------- Add to cart (existing AJAX contract, unchanged payload) ---------- */
  function addToCart(productId, button) {
    clampQty();
    var qty = qtyInput ? qtyInput.value : 1;

    if (button) button.classList.add("is-loading");

    $.ajax({
      type: "POST",
      url: window.SOKOHUB_CART_ADD_URL,
      data: {
        product_id: productId,
        product_qty: qty,
        csrfmiddlewaretoken: csrftoken
      },
      success: function (json) {
        var cartQtyEl = document.getElementById("cart_quantity");
        if (cartQtyEl && json && typeof json.qty !== "undefined") {
          cartQtyEl.textContent = json.qty;
        }
        showToast("✓ Product added to your cart");
      },
      error: function (xhr) {
        console.log("ERROR", xhr.responseText);
        showToast("Couldn't add that item — please try again");
      },
      complete: function () {
        if (button) button.classList.remove("is-loading");
      }
    });
  }

  var addCartBtn = document.getElementById("add-cart");
  if (addCartBtn) {
    addCartBtn.addEventListener("click", function (e) {
      e.preventDefault();
      addToCart(this.value, this);
    });
  }

  var stickyAddCartBtn = document.getElementById("sh-sticky-add-cart");
  if (stickyAddCartBtn) {
    stickyAddCartBtn.addEventListener("click", function (e) {
      e.preventDefault();
      addToCart(this.value, this);
    });
  }

  /* ---------- Sticky mobile purchase bar ---------- */
  var stickyBar = document.getElementById("sh-sticky-bar");
  var purchaseRow = document.querySelector(".sh-purchase-row");
  if (stickyBar && purchaseRow && "IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          stickyBar.classList.toggle("is-visible", !entry.isIntersecting);
        });
      },
      { threshold: 0 }
    );
    observer.observe(purchaseRow);
  }

  /* ---------- Info tabs ---------- */
  var tabs = document.querySelectorAll(".sh-tab");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (t) {
        t.classList.remove("is-active");
        t.setAttribute("aria-selected", "false");
      });
      this.classList.add("is-active");
      this.setAttribute("aria-selected", "true");

      document.querySelectorAll(".sh-tab-panel").forEach(function (panel) {
        panel.hidden = true;
      });
      var panel = document.getElementById(this.getAttribute("aria-controls"));
      if (panel) panel.hidden = false;
    });
  });
})();