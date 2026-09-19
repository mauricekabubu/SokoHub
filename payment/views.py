from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.models import ShippingAddress, Order, OrderItem
from payment.forms import ShippingForm, PaymentForm, MpesaPaymentForm
from django.contrib import messages
from django.contrib.auth.models import User
from store.models import Product, Profile

import ipaddress
import json
import logging

from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import MpesaTransaction
from .payment import apply_stk_callback, reconcile_transaction, initiate_stk_push
import logging


logger = logging.getLogger(__name__)


# Session key holding CheckoutRequestIDs this browser is allowed to poll.
# (Was previously defined further down the file; moved up so both
# process_order and mpesa_status can use it — same constant, same value.)
SESSION_TXN_KEY = "mpesa_checkout_request_ids"

ALLOWED_PAYMENT_METHODS = {"mpesa", "cash_on_delivery", "card"}


# Create your views here.

def payment_success(request):
    
    return render(request, "payment/payment_success.html", {})

def checkout(request):
    # Get the cart
    cart = Cart(request)
    print("CART SESSION:", cart.cart)
    cart_products = cart.get_prods  
    quantities = cart.get_quants 
    totals = cart.cart_total()  
    
    if request.user.is_authenticated:
        # Shipping User
        shipping_user = ShippingAddress.objects.get(user=request.user)
        # Shipping Form
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        
        return render(request, "payment/checkout.html", {"cart_products":cart_products, "quantities":quantities,"totals":totals,"shipping_form":shipping_form})
    
    else:         
        shipping_form = ShippingForm(request.POST or None)
      
        return render(request, "payment/checkout.html", {"cart_products":cart_products, "quantities":quantities,"totals":totals,"shipping_form":shipping_form})
    
    
def billing_info(request):
    if request.method == "POST":
        # Get the cart
        cart = Cart(request)
        print("CART SESSION:", cart.cart)
        cart_products = cart.get_prods  
        quantities = cart.get_quants 
        totals = cart.cart_total()  
        
        # Create a Shipping Session
        my_shipping = request.POST
        request.session["my_shipping"] = my_shipping

        # Payment-method selector + M-Pesa phone number form.
        # (Previously this context var was named "billing_form" and pointed
        # at the raw card-capture PaymentForm, which was rendered via
        # {{ billing_form.as_p }} in the template but is no longer used —
        # collecting raw card numbers/CVVs isn't something we do. The
        # template's phone field already expected a "payment_form" variable;
        # this wires it up.)
        payment_form = MpesaPaymentForm()

        # if user is authenicated
        if request.user.is_authenticated:
            return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities,"totals":totals,"shipping_info":request.POST, "payment_form":payment_form})
        
        else:
            # Get Shipping Form
            shipping_form = request.POST   
            print(shipping_form)                 
            return render(request, "payment/billing_info.html", {"cart_products":cart_products, "quantities":quantities,"totals":totals,"shipping_form":shipping_form, "payment_form":payment_form, "shipping_info":request.POST})
                        
        
    
    else:
        messages.error(request, ("Access Denied!"))
        
        return redirect("home")


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _build_shipping_address(my_shipping):
    return (
        f"{my_shipping['shipping_address1']}\n"
        f"{my_shipping['shipping_address2']}\n"
        f"{my_shipping['shipping_city']}\n"
        f"{my_shipping['shipping_state']}\n"
        f"{my_shipping['shipping_zipcode']}\n"
        f"{my_shipping['shipping_country']}\n"
    )


def _create_order_with_items(request, my_shipping, cart_products, quantities, totals, payment_method):
    """Shared order + order-item creation, used by every payment method.
    Only the payment-specific branch in process_order differs afterward."""

    full_name = my_shipping["shipping_full_name"]
    email = my_shipping["shipping_email"]
    shipping_address = _build_shipping_address(my_shipping)
    amount_paid = totals

    order_kwargs = dict(
        full_name=full_name,
        email=email,
        shipping_address=shipping_address,
        amount_paid=amount_paid,
        payment_method=payment_method,
        payment_status="pending",
    )
    if request.user.is_authenticated:
        order_kwargs["user"] = request.user

    create_order = Order(**order_kwargs)
    create_order.save()

    order_id = create_order.pk

    for product in cart_products():
        if product.is_sale:
            price = product.sale_price
        else:
            price = product.price

        for key, value in quantities().items():
            if int(key) == product.id:
                item_kwargs = dict(order_id=order_id, product_id=product.id, price=price, quantity=value)
                if request.user.is_authenticated:
                    item_kwargs["user"] = request.user
                OrderItem(**item_kwargs).save()

    # Clear the cart (session + Profile.old_cart), same as the original flow.
    for key in list(request.session.keys()):
        if key == "session_key":
            del request.session[key]

    if request.user.is_authenticated:
        Profile.objects.filter(user__id=request.user.id).update(old_cart="")

    request.session.pop("my_shipping", None)

    return create_order


def process_order(request):
    if request.method != "POST":
        messages.error(request, "Access Denied")
        return redirect("home")

    # Get the cart
    cart = Cart(request)
    print("CART SESSION:", cart.cart)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()

    # Empty-cart protection (preserved).
    if not cart_products():
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Your cart is empty."}, status=400)
        messages.error(request, "Your cart is empty.")
        return redirect("cart_summary")

    payment_method = request.POST.get("payment_method")

    # Never trust the frontend alone.
    if payment_method not in ALLOWED_PAYMENT_METHODS:
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Please select a valid payment method."}, status=400)
        messages.error(request, "Please select a valid payment method.")
        return redirect("billing_info")

    payment_form = MpesaPaymentForm(request.POST or None)

    if payment_method == "mpesa" and not payment_form.is_valid():
        if _is_ajax(request):
            return JsonResponse({"ok": False, "errors": payment_form.errors}, status=400)
        messages.error(request, "Enter a valid M-Pesa phone number.")
        return redirect("billing_info")

    # Card payments aren't wired to a gateway yet — don't pretend they
    # succeeded, and don't create an order we can't actually collect on.
    # If/when a provider (e.g. Stripe) is integrated, replace this block
    # with the real charge-creation call and let it fall through to
    # _create_order_with_items like the other two methods.
    if payment_method == "card":
        error_message = "Card payments aren't available yet — please choose M-Pesa or Cash on Delivery."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": error_message}, status=400)
        messages.error(request, error_message)
        return redirect("checkout")

    # Get Shipping Data Session
    my_shipping = request.session.get("my_shipping")
    if not my_shipping:
        messages.error(request, "Missing shipping information.")
        return redirect("checkout")

    create_order = _create_order_with_items(
        request, my_shipping, cart_products, quantities, totals, payment_method
    )

    if payment_method == "cash_on_delivery":
        messages.success(request, "Order placed — pay cash on delivery.")
        return redirect("home")

    # payment_method == "mpesa"
    try:
        stk = initiate_stk_push(
            order=create_order,
            phone_number=payment_form.cleaned_data["mpesa_phone_number"],
            amount=totals,
        )
    except Exception:
        logger.exception("Failed to initiate M-Pesa STK push for order %s", create_order.pk)
        error_message = "We couldn't reach M-Pesa. Please try again."
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": error_message}, status=502)
        messages.error(request, error_message)
        return redirect("checkout")

    txn_ids = request.session.get(SESSION_TXN_KEY, [])
    txn_ids.append(stk.checkout_request_id)
    request.session[SESSION_TXN_KEY] = txn_ids

    if _is_ajax(request):
        return JsonResponse({"ok": True, "checkout_request_id": stk.checkout_request_id})

    messages.success(request, "M-Pesa prompt sent. Check your phone.")
    return redirect("checkout")
        

def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True)
        
        if request.POST:
            status = request.POST["shipping_status"]   
            num = request.POST["num"]    
            
            # Grab the Order
            order = Order.objects.filter(id=num)           
                
            # Update status
            order.update(shipped=False)
            
            messages.success(request, "Shipping status updated")
            return redirect("home")
                
                    
        return render(request, "payment/shipped_dash.html", {"orders":orders})
    else:
        messages.error(request, ("Access denied!"))
        
        return redirect("home")
    


def not_shipped_dash(request):    
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=False)
        
        if request.POST:
            status = request.POST["shipping_status"]   
            num = request.POST["num"] 
            # Grab the Order
            order = Order.objects.filter(id=num)
                          
                
            # Update status
            order.update(shipped=True)
            
            messages.success(request, "Shipping status updated")
            return redirect("home")
        
                        
        return render(request, "payment/not_shipped_dash.html", {"orders":orders})
    else:
        messages.error(request, ("Access denied!"))
        
        return redirect("home")
    

def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        # Get Order
        order = Order.objects.get(id=pk)
        
        # Get the OrderItems
        items = OrderItem.objects.filter(order=pk)
        
        if request.POST:
            status = request.POST["shipping_status"]
            # Check if True or False
            if status == "true":
                # Get Order
                order = Order.objects.filter(id=pk)
                
                # Update status
                order.update(shipped=True)
            
            else:
                # Get Order
                order = Order.objects.filter(id=pk)
                
                # Update status
                order.update(shipped=True)
            
            messages.success(request, "Shipping status updated")
            return redirect("home")
                        
        return render(request, "payment/orders.html", {"order":order,"items":items})
    else:
        messages.error(request, ("Access denied!"))
        
        return redirect("home")
    

"""
payments/views.py  —  M-Pesa webhook + status polling.

Two endpoints:
  * mpesa_callback  — Safaricom posts here. CSRF-exempt (no browser session
                      involved). Every other checkout form stays CSRF-protected.
  * mpesa_status    — the browser polls here. Session-scoped, read-only.
"""

# Optional hardening: only accept callbacks from Safaricom's published ranges.
# Leave MPESA_CALLBACK_ALLOWED_IPS unset to skip the check (useful with ngrok).
DEFAULT_SAFARICOM_IPS = [
    "196.201.214.0/24",
    "196.201.213.0/24",
    "196.201.212.0/24",
]


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _ip_allowed(request):
    networks = getattr(settings, "MPESA_CALLBACK_ALLOWED_IPS", None)
    if not networks:
        return True
    if networks is True:
        networks = DEFAULT_SAFARICOM_IPS
    try:
        ip = ipaddress.ip_address(_client_ip(request))
    except ValueError:
        return False
    return any(ip in ipaddress.ip_network(net) for net in networks)


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """
    Safaricom's result webhook. Must always answer 200 with the Daraja ack shape,
    otherwise Safaricom retries indefinitely. Processing is idempotent.
    """
    if not _ip_allowed(request):
        logger.warning("Rejected M-Pesa callback from %s", _client_ip(request))
        return HttpResponseForbidden("Forbidden")

    try:
        body = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        logger.warning("Malformed M-Pesa callback body")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    stk_callback = (body.get("Body") or {}).get("stkCallback")
    if not stk_callback:
        logger.warning("M-Pesa callback missing Body.stkCallback")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    try:
        apply_stk_callback(stk_callback, raw_body=body)
    except Exception:  # never leak a 500 back to Safaricom
        logger.exception("Error processing M-Pesa callback")

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

@require_GET
def mpesa_status(request, checkout_request_id):
    """
    Polled by the checkout page.

    - Successful payment -> payment success page
    - Cancelled/failed/timeout -> restore cart
    - Still processing -> leave cart empty and keep polling
    """

    allowed = request.session.get(SESSION_TXN_KEY, [])

    if checkout_request_id not in allowed:
        return JsonResponse({"status": "unknown"}, status=404)

    try:
        txn = MpesaTransaction.objects.select_related("order").get(
            checkout_request_id=checkout_request_id
        )
    except MpesaTransaction.DoesNotExist:
        return JsonResponse({"status": "unknown"}, status=404)

    # If the callback hasn't arrived yet, ask Daraja directly.
    if not txn.is_terminal:
        txn = reconcile_transaction(txn)

    # Restore cart only after a FINAL unsuccessful payment.
    if txn.status in {
        MpesaTransaction.Status.CANCELLED,
        MpesaTransaction.Status.FAILED,
        MpesaTransaction.Status.TIMEOUT,
    }:
        restore_key = f"mpesa_cart_restored_{txn.order.pk}"

        if not request.session.get(restore_key):
            restore_order_to_cart(request, txn.order)

            # Prevent duplicate restoration on the next poll.
            request.session[restore_key] = True
            request.session.modified = True

    payload = {
        "status": txn.status,
        "is_terminal": txn.is_terminal,
        "message": txn.result_description or "",
    }

    if txn.is_successful:
        payload["receipt"] = txn.mpesa_receipt_number or ""

        payload["redirect_url"] = getattr(
            settings,
            "MPESA_SUCCESS_URL",
            None,
        ) or reverse("payment_success")

    return JsonResponse(payload)


def restore_order_to_cart(request, order):
    """
    Restore the products from a failed/cancelled M-Pesa order
    back into the user's session cart.

    Safe to call multiple times for the same order.
    """
    session_cart = request.session.get("cart", {})

    for item in order.orderitem_set.select_related("product").all():
        if not item.product:
            continue

        product_id = str(item.product.id)
        current_quantity = int(session_cart.get(product_id, 0))

        session_cart[product_id] = current_quantity + int(item.quantity)

    request.session["cart"] = session_cart
    request.session.modified = True

    logger.info(
        "Restored order %s items to cart after unsuccessful M-Pesa payment",
        order.pk,
    )

