from django.contrib import admin
from .models import Customer, Category, Product, Order, Profile, NewsletterSubscriber, Message
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Customer)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(Profile)
admin.site.register(NewsletterSubscriber)
admin.site.register(Message)


#Mix profile info and user info
class ProfileInline(admin.StackedInline):
    model = Profile
    
#Extend the User Model
class UserAdmin(admin.ModelAdmin):
    model = User
    field = ["username", "first_name", "last_name", "email"]
    inlines = [ProfileInline]
    
# Unregister User
admin.site.unregister(User)

# Re-Register User
admin.site.register(User, UserAdmin)


