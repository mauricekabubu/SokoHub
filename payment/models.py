from django.db import models
from django.contrib.auth.models import User 
from store.models import Product
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from django.db import models


# Create your models here.

class ShippingAddress(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    shipping_full_name = models.CharField(max_length=255)
    shipping_email = models.CharField(max_length=100)
    shipping_address1 = models.CharField(max_length=255)
    shipping_address2 = models.CharField(max_length=255, null=True, blank=True)
    shipping_city = models.CharField(max_length=255, null=True, blank=True)
    shipping_state = models.CharField(max_length=255, null=True, blank=True)
    shipping_zipcode = models.CharField(max_length=255, null=True, blank=True)
    shipping_country = models.CharField(max_length=255)
    
    class Meta:
        verbose_name_plural = "Shipping_Address"
        
    def __str__(self):
        return f"Shipping Address - {str(self.id)}"
    
    
#Creating the Shipping address by default
def create_shipping(sender, instance, created, **kwargs):
    #Sender=User and instance current instance created
    if created:
        user_shipping = ShippingAddress(user=instance)
        user_shipping.save()
    
# Automate the shipping thing
post_save.connect(create_shipping, sender=User)
        
    
# Creating Order Model
class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("mpesa", "M-Pesa"),
        ("cash_on_delivery", "Cash on Delivery"),
        ("card", "Card"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=250)
    email = models.EmailField(max_length=250)
    shipping_address = models.TextField(max_length=15000)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2)
    date_ordered = models.DateTimeField(auto_now_add=True)
    shipped = models.BooleanField(default=False)
    date_shipped = models.DateTimeField(blank=True, null=True)

    # New: which method the customer chose, and whether it has actually
    # settled. mpesa flips to "paid" only from the Daraja callback
    # (apply_stk_callback) — never on STK initiation.
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="mpesa"
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )

    def __str__(self):
        return f"Order - {str(self.id)}"
    
# auto add shipping date

@receiver(pre_save, sender=Order)
def set_shipped_date_on_update(sender, instance, **kwargs):

    if instance.pk:
        now = timezone.now()

        obj = sender._default_manager.get(pk=instance.pk)

        if instance.shipped and not obj.shipped:
            instance.date_shipped = now


# Create Order Items model
class OrderItem(models.Model):
    # ForeignKeys
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    
    # Items
    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=15, decimal_places=2)
    
    
    def __str__(self):
        return f"Order Item - {str(self.id)}"


# Keeps this module portable: point at your real Order model via settings.
#ORDER_MODEL = getattr(settings, "MPESA_ORDER_MODEL", "orders.Order")


class MpesaTransaction(models.Model):
    """One STK Push attempt against one order. An order may have several
    (customer cancels, retries, mistypes the number)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"          # row created, push not yet sent
        SENT = "sent", "Prompt sent"            # Daraja accepted the push
        SUCCESS = "success", "Successful"       # callback confirmed payment
        FAILED = "failed", "Failed"             # wrong PIN, no funds, etc.
        CANCELLED = "cancelled", "Cancelled"    # user dismissed the prompt
        TIMEOUT = "timeout", "Timed out"        # no response in time

    TERMINAL_STATUSES = {Status.SUCCESS, Status.FAILED, Status.CANCELLED, Status.TIMEOUT}

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="mpesa_transactions",
    )
    phone_number = models.CharField(max_length=15, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    merchant_request_id = models.CharField(max_length=64, blank=True, db_index=True)
    checkout_request_id = models.CharField(
        max_length=64, blank=True, unique=True, null=True, db_index=True
    )
    mpesa_receipt_number = models.CharField(
        max_length=32, blank=True, null=True, unique=True
    )

    result_code = models.IntegerField(null=True, blank=True)
    result_description = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    # Full callback body, for auditing and disputes. Never contains a PIN.
    raw_callback = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = "M-Pesa transaction"
        verbose_name_plural = "M-Pesa transactions"

    def __str__(self):
        return f"{self.checkout_request_id or 'unsent'} — {self.get_status_display()}"

    @property
    def is_terminal(self):
        return self.status in self.TERMINAL_STATUSES

    @property
    def is_successful(self):
        return self.status == self.Status.SUCCESS

    def masked_phone(self):
        """254712345678 -> 2547****5678 (for UI and logs)."""
        if len(self.phone_number) < 8:
            return "*" * len(self.phone_number)
        return f"{self.phone_number[:4]}****{self.phone_number[-4:]}"