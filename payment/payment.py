"""
payments/services.py

All M-Pesa business logic lives here so views stay thin and the flow is testable.

Two responsibilities:
  1. initiate_stk_push()  — called from the checkout view.
  2. apply_stk_callback() — called from the webhook (and from the status poll
                            fallback). This is the ONLY place an order becomes paid.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import MpesaTransaction
from .mpesa_client import MpesaClient, MpesaError

logger = logging.getLogger(__name__)

# Daraja ResultCodes we can map to a friendlier state.
CANCELLED_CODES = {1032}
TIMEOUT_CODES = {1037, 1019}


# ---------------------------------------------------------------------------
# ADAPTATION POINT 1 of 2 — wire these to your real Order model.
# ---------------------------------------------------------------------------
def mark_order_paid(order, txn):
    """
    Called exactly once, inside a transaction, after M-Pesa confirms payment.

    Replace the body with your project's real fields. The guarded version below
    covers the common SokoHub/Django-shop field names and is a no-op for fields
    you don't have — but you should make it explicit.
    """
    updated = []

    if hasattr(order, "paid"):
        order.paid = True
        updated.append("paid")
    if hasattr(order, "is_paid"):
        order.is_paid = True
        updated.append("is_paid")
    if hasattr(order, "payment_status"):
        order.payment_status = "paid"
        updated.append("payment_status")
    if hasattr(order, "status") and "payment_status" not in updated:
        order.status = "confirmed"
        updated.append("status")
    if hasattr(order, "amount_paid"):
        order.amount_paid = txn.amount
        updated.append("amount_paid")
    if hasattr(order, "paid_at"):
        order.paid_at = timezone.now()
        updated.append("paid_at")

    if updated:
        order.save(update_fields=updated)
    else:  # pragma: no cover
        order.save()

    logger.info("Order %s marked paid via M-Pesa receipt %s",
                order.pk, txn.mpesa_receipt_number)


def order_total(order):
    """
    ADAPTATION POINT 1b — how to read the authoritative total off an order.
    Never accept a total from the request.
    """
    for field in ("total", "grand_total", "amount", "amount_paid", "total_price"):
        value = getattr(order, field, None)
        if value:
            return Decimal(str(value))
    raise ValueError(f"Cannot determine total for order {order.pk}")


# ---------------------------------------------------------------------------
# Initiation
# ---------------------------------------------------------------------------
def initiate_stk_push(order, phone_number, amount, account_reference=None):
    """
    Create a MpesaTransaction row, then ask Daraja to prompt the customer.

    `amount` must already have been computed server-side by the caller.
    Returns the MpesaTransaction. Raises MpesaError if the push was not accepted.
    """
    txn = MpesaTransaction.objects.create(
        order=order,
        phone_number=phone_number,
        amount=Decimal(str(amount)),
        status=MpesaTransaction.Status.PENDING,
    )

    client = MpesaClient()
    try:
        response = client.stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference or f"SOKO{order.pk}",
            transaction_desc=f"Order {order.pk}",
        )
    except MpesaError as exc:
        txn.status = MpesaTransaction.Status.FAILED
        txn.result_description = str(exc)[:255]
        txn.completed_at = timezone.now()
        txn.save(update_fields=["status", "result_description", "completed_at"])
        logger.warning("STK push failed for order %s: %s", order.pk, exc)
        raise

    txn.merchant_request_id = response.get("MerchantRequestID", "")
    txn.checkout_request_id = response.get("CheckoutRequestID", "")
    txn.status = MpesaTransaction.Status.SENT
    txn.save(update_fields=["merchant_request_id", "checkout_request_id", "status"])

    logger.info(
        "STK push sent: order=%s checkout_request_id=%s phone=%s",
        order.pk, txn.checkout_request_id, txn.masked_phone(),
    )
    return txn


# ---------------------------------------------------------------------------
# Callback handling — idempotent, the single source of truth
# ---------------------------------------------------------------------------
def _extract_metadata(stk_callback):
    items = (stk_callback.get("CallbackMetadata") or {}).get("Item") or []
    return {item.get("Name"): item.get("Value") for item in items if item.get("Name")}


def apply_stk_callback(stk_callback, raw_body=None):
    """
    Process one Body.stkCallback payload.

    Safe to call repeatedly with the same payload.
    A transaction that has already reached a terminal state is left alone.
    """

    checkout_request_id = stk_callback.get("CheckoutRequestID")

    if not checkout_request_id:
        logger.warning("M-Pesa callback missing CheckoutRequestID")
        return None

    with transaction.atomic():
        try:
            txn = (
                MpesaTransaction.objects
                .select_for_update()
                .select_related("order")
                .get(checkout_request_id=checkout_request_id)
            )
        except MpesaTransaction.DoesNotExist:
            logger.warning(
                "M-Pesa callback for unknown CheckoutRequestID %s",
                checkout_request_id,
            )
            return None

        if txn.is_terminal:
            logger.info(
                "Duplicate M-Pesa callback ignored for %s",
                checkout_request_id,
            )
            return txn

        result_code = stk_callback.get("ResultCode")

        try:
            result_code = int(result_code)
        except (TypeError, ValueError):
            result_code = -1

        txn.result_code = result_code
        txn.result_description = str(
            stk_callback.get("ResultDesc", "")
        )[:255]

        txn.raw_callback = (
            raw_body
            if raw_body is not None
            else stk_callback
        )

        # ------------------------------------------
        # SUCCESS
        # ------------------------------------------

        if result_code == 0:

            meta = _extract_metadata(stk_callback)

            txn.mpesa_receipt_number = (
                meta.get("MpesaReceiptNumber") or None
            )

            paid_amount = Decimal(
                str(meta.get("Amount", txn.amount))
            )

            expected = Decimal(
                str(txn.amount)
            ).quantize(Decimal("1"))

            if paid_amount.quantize(Decimal("1")) != expected:

                txn.status = MpesaTransaction.Status.FAILED

                txn.result_description = (
                    f"Amount mismatch: paid {paid_amount}, "
                    f"expected {expected}"
                )[:255]

                txn.completed_at = timezone.now()

                txn.save()

                logger.error(
                    "M-Pesa amount mismatch on %s: paid=%s expected=%s",
                    checkout_request_id,
                    paid_amount,
                    expected,
                )

                return txn

            txn.status = MpesaTransaction.Status.SUCCESS
            txn.completed_at = timezone.now()

            txn.save()

            mark_order_paid(txn.order, txn)

        # ------------------------------------------
        # FAILED / CANCELLED / TIMEOUT
        # ------------------------------------------

        else:

            if result_code in CANCELLED_CODES:
                txn.status = MpesaTransaction.Status.CANCELLED

            elif result_code in TIMEOUT_CODES:
                txn.status = MpesaTransaction.Status.TIMEOUT

            else:
                txn.status = MpesaTransaction.Status.FAILED

            txn.completed_at = timezone.now()

            txn.save()

            logger.info(
                "M-Pesa payment not completed (%s): %s",
                result_code,
                txn.result_description,
            )

    return txn


def reconcile_transaction(txn):
    """
    Fallback used by the status endpoint when a transaction is still
    pending/sent and the callback hasn't arrived.
    """

    if txn.is_terminal or not txn.checkout_request_id:
        return txn

    try:
        data = MpesaClient().query_stk_status(
            txn.checkout_request_id
        )

    except MpesaError as exc:
        logger.debug(
            "STK query failed for %s: %s",
            txn.checkout_request_id,
            exc,
        )
        return txn

    if "ResultCode" not in data:
        return txn

    try:
        result_code = int(data.get("ResultCode"))
    except (TypeError, ValueError):
        return txn

    # Still processing.
    if result_code == 4999:
        logger.info(
            "M-Pesa transaction %s is still processing",
            txn.checkout_request_id,
        )
        return txn

    return apply_stk_callback(
        {
            "CheckoutRequestID": txn.checkout_request_id,
            "MerchantRequestID": data.get(
                "MerchantRequestID",
                "",
            ),
            "ResultCode": result_code,
            "ResultDesc": data.get(
                "ResultDesc",
                "",
            ),
        },
        raw_body=data,
    ) or txn