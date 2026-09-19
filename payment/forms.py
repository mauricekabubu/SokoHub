from django import forms
from .models import ShippingAddress

import re

from django import forms
from django.core.exceptions import ValidationError


class ShippingForm(forms.ModelForm):
    shipping_full_name = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Shipping Full name'}), required=True)
    shipping_address1 = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Shipping Address1'}), required=True)
    shipping_address2 = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Shipping Address2'}), required=False)
    shipping_email = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Shipping Email Address'}), required=True)
    shipping_city = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'City'}), required=False)
    shipping_state = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'State'}), required=False)
    shipping_zipcode = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Zipcode'}), required=False)
    shipping_country = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Country'}), required=True)

    class Meta:
        model = ShippingAddress
        fields = ["shipping_full_name","shipping_address1","shipping_address2","shipping_email",
                  "shipping_city","shipping_state","shipping_zipcode","shipping_country"]

        exclude = ["user"]


# NOTE: PaymentForm (raw card_number / card_cvv_number / ... fields) is kept
# here only so nothing that already imports it breaks. It is no longer
# instantiated or rendered anywhere in the checkout flow — collecting raw
# card details directly violates the "no raw card data in our DB or POST
# payload" requirement, and MpesaPaymentForm below now owns payment-method
# selection instead. Safe to delete once you've confirmed nothing else
# references it.
class PaymentForm(forms.Form):
    card_name = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card Name'}), required=True)
    card_number = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card Number'}), required=True)
    card_exp_date = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card Expiry date'}), required=True)
    card_cvv_number = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card CVV Number'}), required=True)
    card_address1 = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card Address1'}), required=True)
    card_address2 = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card Address2'}), required=True)
    card_city = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card City'}), required=True)
    card_state = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card State'}), required=True)
    card_zipcode = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card ZipCode'}), required=True)
    card_country = forms.CharField(label="", widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Card Country'}), required=True)


# Accepts: 0712345678, 0112345678, 712345678, 254712345678, +254712345678,
#          and the same with spaces/dashes.
_CLEAN_RE = re.compile(r"[\s\-\(\)]")
_SAFARICOM_LOCAL_RE = re.compile(r"^(?:\+?254|0)?(7\d{8}|1\d{8})$")


def normalize_kenyan_msisdn(value):
    """
    Return a phone number in Daraja's required 2547XXXXXXXX / 2541XXXXXXXX form.
    Raises ValidationError on anything else.
    """
    if not value:
        raise ValidationError("Enter the M-Pesa number to receive the prompt.")

    cleaned = _CLEAN_RE.sub("", str(value))
    match = _SAFARICOM_LOCAL_RE.match(cleaned)
    if not match:
        raise ValidationError(
            "Enter a valid Safaricom number in the format 254712345678."
        )
    return f"254{match.group(1)}"


class MpesaPaymentForm(forms.Form):
    """Validates the payment-method selection and, when relevant, the M-Pesa
    phone number. Your ShippingForm is untouched."""

    PAYMENT_METHOD_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("cash_on_delivery", "Cash on Delivery"),
        ("card", "Card"),
    ]

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        initial="mpesa",
        widget=forms.RadioSelect,
    )
    mpesa_phone_number = forms.CharField(
        required=False,
        max_length=20,
        label="M-Pesa Phone Number",
        widget=forms.TextInput(
            attrs={
                "placeholder": "254712345678",
                "inputmode": "numeric",
                "autocomplete": "tel",
                "class": "pm-input",
            }
        ),
        help_text="Enter the M-Pesa number that will receive the payment prompt.",
    )

    def clean(self):
        data = super().clean()
        if data.get("payment_method") == "mpesa":
            try:
                data["mpesa_phone_number"] = normalize_kenyan_msisdn(
                    data.get("mpesa_phone_number")
                )
            except ValidationError as exc:
                self.add_error("mpesa_phone_number", exc)
        return data