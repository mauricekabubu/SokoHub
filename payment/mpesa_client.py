"""
payments/mpesa_client.py

Thin, testable wrapper around the Safaricom Daraja API (STK Push / Lipa Na M-Pesa Online).

This module knows NOTHING about orders, carts or Django views. It only speaks HTTP to
Safaricom. All credentials come from Django settings (which read environment variables).
"""

import base64
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

logger = logging.getLogger(__name__)

# Daraja expects the timestamp in East Africa Time.
NAIROBI_TZ = timezone.get_fixed_timezone(180)  # UTC+03:00

BASE_URLS = {
    "sandbox": "https://sandbox.safaricom.co.ke",
    "production": "https://api.safaricom.co.ke",
}

ACCESS_TOKEN_CACHE_KEY = "mpesa:access_token"
# Daraja tokens live 3599s; refresh a little early.
ACCESS_TOKEN_TTL = 3000

CONSUMER_KEY    = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
SHORT_CODE      = os.getenv("SHORT_CODE")
PASSKEY         = os.getenv("PASSKEY")
PHONE_NUMBER    = os.getenv("PHONE_NUMBER")
INITIATOR_NAME  = os.getenv("INITIATOR_NAME")
INITIATOR_PASSWORD = os.getenv("INITIATOR_PASSWORD")
PARTY_A         = os.getenv("PARTY_A")
PARTY_B         = os.getenv("PARTY_B")
C2B_SHORT_CODE = os.getenv("C2B_SHORT_CODE", SHORT_CODE)  # default to SHORT_CODE if not set
C2B_SAFARICOM_SANDBOX_URL = os.getenv("C2B_SAFARICOM_SANDBOX_URL")
SAFARICOM_SANDBOX_TOKEN_URL = os.getenv("SAFARICOM_SANDBOX_TOKEN_URL")
SAFARICOM_SANDBOX_STK_PUSH_URL = os.getenv("SAFARICOM_SANDBOX_STK_PUSH_URL")

# Callback URL must be a publicly reachable URL (e.g. ngrok tunnel).
# Set MPESA_CALLBACK_URL in your .env file — never hardcode it here.
CALLBACK_URL        = os.getenv("CALLBACK_URL")
C2B_VALIDATION_URL  = os.getenv("C2B_VALIDATION_URL")
C2B_CONFIRMATION_URL= os.getenv("C2B_CONFIRMATION_URL")

print("=" * 40)
print("SHORT_CODE      =", repr(SHORT_CODE))
print("C2B_SHORT_CODE  =", repr(C2B_SHORT_CODE))
print("CALLBACK_URL    =", repr(CALLBACK_URL))
print("VALIDATION_URL  =", repr(C2B_VALIDATION_URL))
print("CONFIRMATION_URL=", repr(C2B_CONFIRMATION_URL))
print("=" * 40)



class MpesaError(Exception):
    """Raised when Daraja rejects a request or is unreachable."""

    def __init__(self, message, payload=None):
        super().__init__(message)
        self.payload = payload or {}


class MpesaClient:
    def __init__(self):
        self.consumer_key = self._required("CONSUMER_KEY")
        self.consumer_secret = self._required("CONSUMER_SECRET")
        self.shortcode = str(self._required("SHORT_CODE"))
        self.passkey = self._required("PASSKEY")
        self.callback_url = self._required("CALLBACK_URL")
        self.environment = getattr(settings, "MPESA_ENVIRONMENT", "sandbox")
        self.timeout = getattr(settings, "MPESA_HTTP_TIMEOUT", 30)

        if self.environment not in BASE_URLS:
            raise MpesaError(f"Unknown MPESA_ENVIRONMENT: {self.environment!r}")
        self.base_url = BASE_URLS[self.environment]

    @staticmethod
    def _required(name):
        value = os.getenv(name)
        if not value:
            raise MpesaError(
                f"{name} is not configured. Set it as an environment variable."
            )
        return value

    # ------------------------------------------------------------------ auth

    def get_access_token(self, force_refresh=False):
        if not force_refresh:
            token = cache.get(ACCESS_TOKEN_CACHE_KEY)
            if token:
                return token

        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        try:
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                timeout=self.timeout,
            )
            response.raise_for_status()
            token = response.json().get("access_token")
        except requests.RequestException as exc:
            logger.exception("M-Pesa access token request failed")
            raise MpesaError("Could not reach M-Pesa. Please try again.") from exc

        if not token:
            raise MpesaError("M-Pesa did not return an access token.")

        cache.set(ACCESS_TOKEN_CACHE_KEY, token, ACCESS_TOKEN_TTL)
        return token

    def _headers(self, force_refresh=False):
        return {
            "Authorization": f"Bearer {self.get_access_token(force_refresh)}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------- utilities

    def _password(self, timestamp):
        raw = f"{self.shortcode}{self.passkey}{timestamp}".encode()
        return base64.b64encode(raw).decode()

    @staticmethod
    def _timestamp():
        return datetime.now(NAIROBI_TZ).strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _amount(value):
        """Daraja only accepts whole shillings."""
        return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def _post(self, path, payload):
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(
                url, json=payload, headers=self._headers(), timeout=self.timeout
            )
            if response.status_code == 401:
                # Token may have been revoked early; retry once with a fresh one.
                response = requests.post(
                    url,
                    json=payload,
                    headers=self._headers(force_refresh=True),
                    timeout=self.timeout,
                )
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.exception("M-Pesa request to %s failed", path)
            raise MpesaError("Could not reach M-Pesa. Please try again.") from exc

        if response.status_code >= 400:
            logger.warning("M-Pesa %s returned %s: %s", path, response.status_code, data)
            raise MpesaError(
                data.get("errorMessage") or "M-Pesa rejected the request.", data
            )
        return data

    # ------------------------------------------------------------- endpoints

    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """
        Send an STK Push prompt to `phone_number`.

        `amount` MUST be computed server-side from the cart/order total.
        Returns the raw Daraja response containing MerchantRequestID and
        CheckoutRequestID.
        """
        timestamp = self._timestamp()
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": getattr(
                settings, "MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline"
            ),
            "Amount": self._amount(amount),
            "PartyA": phone_number,
            "PartyB": getattr(settings, "MPESA_PARTY_B", self.shortcode),
            "PhoneNumber": phone_number,
            "CallBackURL": self.callback_url,
            "AccountReference": str(account_reference)[:12],
            "TransactionDesc": str(transaction_desc)[:13],
        }
        data = self._post("/mpesa/stkpush/v1/processrequest", payload)

        if str(data.get("ResponseCode")) != "0":
            raise MpesaError(
                data.get("ResponseDescription") or "M-Pesa could not send the prompt.",
                data,
            )
        return data

    def query_stk_status(self, checkout_request_id):
        """
        Ask Daraja for the final state of a push. Used as a safety net when the
        callback is slow or never arrives (e.g. local dev without a public URL).
        """
        timestamp = self._timestamp()
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }
        return self._post("/mpesa/stkpushquery/v1/query", payload)