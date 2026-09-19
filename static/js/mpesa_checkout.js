/* SokoHub — checkout payment flow (M-Pesa, Cash on Delivery, Card).
   No credentials, no amounts, no secrets here. The browser only reports status;
   the server decides whether an order is paid.

   Cash on Delivery and Card submit as a normal form POST (full page load) —
   the server creates/validates the order and redirects. Only M-Pesa is
   intercepted for the STK Push + polling experience. */

(function () {
  "use strict";

  var form = document.getElementById("checkout-form");
  if (!form) return;

  var payBtn    = document.getElementById("btn-pay");
  var payLabel  = payBtn && payBtn.querySelector(".btn-pay-label");
  var phone     = document.getElementById("id_mpesa_phone_number");
  var errorEl   = document.getElementById("pm-phone-error");
  var statusEl  = document.getElementById("pm-status");
  var titleEl   = document.getElementById("pm-status-title");
  var textEl    = document.getElementById("pm-status-text");
  var statusTpl = form.getAttribute("data-status-url") || "";
  var amountText = payBtn ? payBtn.getAttribute("data-amount-text") || "" : "";

  var POLL_MS = 3000;
  var MAX_WAIT_MS = 120000;
  var submitting = false;
  var timer = null;

  var PANEL_IDS = {
    mpesa: "pm-mpesa-fields",
    cash_on_delivery: "pm-cod-fields",
    card: "pm-card-fields"
  };

  var BUTTON_LABELS = {
    mpesa: "Pay Now",
    cash_on_delivery: "Place Order",
    card: "Continue to Payment"
  };

  var MPESA_IDLE_LABEL = buttonText("mpesa");

  /* ------------------------------------------------------------- helpers */

  function buttonText(method) {
    var prefix = BUTTON_LABELS[method] || BUTTON_LABELS.mpesa;
    return amountText ? prefix + " — " + amountText : prefix;
  }

  function setOption(label) {
    document.querySelectorAll(".pm-option").forEach(function (el) {
      el.classList.toggle("is-selected", el === label);
    });

    var input = label.querySelector("input");
    var value = input ? input.value : "mpesa";

    Object.keys(PANEL_IDS).forEach(function (method) {
      var panel = document.getElementById(PANEL_IDS[method]);
      if (panel) panel.hidden = method !== value;
    });

    if (phone) phone.required = value === "mpesa";

    // Switching away from M-Pesa clears any in-progress status/errors.
    if (value !== "mpesa") {
      showFieldError("");
      if (statusEl) statusEl.hidden = true;
    }

    if (payLabel) payLabel.textContent = buttonText(value);
  }

  document.querySelectorAll("[data-pm-option]").forEach(function (input) {
    input.addEventListener("change", function () {
      setOption(input.closest(".pm-option"));
    });
  });

  function showFieldError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.hidden = !message;
    if (phone) {
      phone.classList.toggle("has-error", Boolean(message));
      if (message) { phone.setAttribute("aria-invalid", "true"); phone.focus(); }
      else phone.removeAttribute("aria-invalid");
    }
  }

  function setStatus(title, text, isError) {
    if (!statusEl) return;
    statusEl.hidden = false;
    statusEl.classList.toggle("is-error", Boolean(isError));
    titleEl.textContent = title;
    textEl.textContent = text || "";
  }

  function lock(locked, labelText) {
    submitting = locked;
    if (!payBtn) return;
    payBtn.disabled = locked;
    if (payLabel && labelText) payLabel.textContent = labelText;
  }

  function reset() {
    if (timer) { clearInterval(timer); timer = null; }
    lock(false, MPESA_IDLE_LABEL);
  }

  /* Client-side pre-check only. The server revalidates and is authoritative. */
  function looksLikeKenyanNumber(value) {
    var cleaned = (value || "").replace(/[\s\-()]/g, "");
    return /^(?:\+?254|0)?(7\d{8}|1\d{8})$/.test(cleaned);
  }

  function csrfToken() {
    var field = form.querySelector("[name=csrfmiddlewaretoken]");
    return field ? field.value : "";
  }

  /* -------------------------------------------------------------- submit */

  form.addEventListener("submit", function (event) {
    var method = form.querySelector("[name=payment_method]:checked");
    if (!method || method.value !== "mpesa") return;   // COD / Card: normal POST

    event.preventDefault();
    if (submitting) return;

    showFieldError("");
    if (!looksLikeKenyanNumber(phone && phone.value)) {
      showFieldError("Enter a valid Safaricom number in the format 254712345678.");
      return;
    }

    lock(true, "Sending M-Pesa payment request…");
    setStatus("Sending M-Pesa payment request…", "");

    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrfToken() }
    })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, data: d }; }); })
      .then(function (result) {
        var data = result.data || {};

        if (!result.ok || !data.ok) {
          if (data.errors && data.errors.mpesa_phone_number) {
            showFieldError(data.errors.mpesa_phone_number[0]);
            statusEl.hidden = true;
          } else {
            setStatus(
              "Payment request failed",
              data.error || "We couldn't reach M-Pesa. Please try again.",
              true
            );
          }
          reset();
          return;
        }

        setStatus(
          "M-Pesa prompt sent",
          "Check your phone and enter your M-Pesa PIN to complete the payment."
        );
        lock(true, "Waiting for payment…");
        startPolling(data.checkout_request_id);
      })
      .catch(function () {
        setStatus("Network error", "Check your connection and try again.", true);
        reset();
      });
  });

  /* ------------------------------------------------------------- polling */

  function statusUrl(id) {
    return statusTpl ? statusTpl.replace("CRID", encodeURIComponent(id))
                     : "/payments/mpesa/status/" + encodeURIComponent(id) + "/";
  }

  function startPolling(checkoutRequestId) {
    if (!checkoutRequestId) return;
    var started = Date.now();
    var announced = false;

    timer = setInterval(function () {
      if (Date.now() - started > MAX_WAIT_MS) {
        setStatus(
          "Payment not confirmed",
          "We didn't receive confirmation in time. Your order has not been charged — you can try again.",
          true
        );
        reset();
        return;
      }

      fetch(statusUrl(checkoutRequestId), {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" }
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (!announced && data.status === "sent") {
            setStatus("Waiting for payment confirmation…",
                      "Keep this page open until the payment is confirmed.");
            announced = true;
          }
          if (!data.is_terminal) return;

          if (data.status === "success") {
            setStatus("Payment confirmed",
                      data.receipt ? "M-Pesa receipt " + data.receipt : "Redirecting…");
            clearInterval(timer);
            timer = null;
            window.location.href = data.redirect_url || "/";
            return;
          }

          var messages = {
            cancelled: "You cancelled the payment request. Nothing was charged.",
            timeout: "The payment request expired. Please try again.",
            failed: data.message || "The payment did not go through. Please try again."
          };
          setStatus("Payment not completed", messages[data.status] || messages.failed, true);
          reset();
        })
        .catch(function () { /* transient; the next tick retries */ });
    }, POLL_MS);
  }

  /* Prefill from the billing phone field if the shop already collects one. */
  if (phone && !phone.value) {
    var billingPhone = form.querySelector(
      "input[name=phone], input[name=billing_phone], input[name$='_phone']"
    );
    if (billingPhone && billingPhone !== phone && billingPhone.value) {
      phone.value = billingPhone.value;
    }
  }

  window.addEventListener("beforeunload", function (e) {
    if (submitting) { e.preventDefault(); e.returnValue = ""; }
  });
})();