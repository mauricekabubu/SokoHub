from django.contrib import admin
from .models import ShippingAddress, Order, OrderItem, MpesaTransaction
from django.contrib.auth.models import User


# Register your models here.
admin.site.register(ShippingAddress)
#admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(MpesaTransaction)


class OrderItemInline(admin.StackedInline):
    model = OrderItem
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ["date_ordered"]

    fields = [
        "user",
        "full_name",
        "email",
        "shipping_address",
        "amount_paid",
        "date_ordered",
        "shipped"
    ]

    inlines = [OrderItemInline]

# Register Order
admin.site.register(Order, OrderAdmin)

    