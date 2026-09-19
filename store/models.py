from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

import datetime

# Create your models here.

#  Create a customer's profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_modified = models.DateTimeField(User, auto_now=True)
    phone = models.CharField(max_length=20, blank=True )
    address1 = models.CharField(max_length=20, blank=True)
    address2 = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=20, blank=True)
    state = models.CharField(max_length=20, blank=True)
    zipcode = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=20, blank=True)
    old_cart = models.CharField(max_length=20, null=True, blank=True)
    
    
    def __str__(self):
        return self.user.username
    
    

#Creating the profile by default
def create_profile(sender, instance, created, **kwargs):
    #Sender=User and instance current instance created
    if created:
        user_profile = Profile(user=instance)
        user_profile.save()
        
    
#Automate the profile thing
post_save.connect(create_profile, sender=User)
    
    
class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='uploads/categories/', blank=True, null=True)
    class Meta:
                
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name
    


class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=50)
    phone = models.CharField(max_length=10)
    password = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
        
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)
    description = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to="uploads/product/")
    
    # Adding some sales details
    is_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(default=0, max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.name

class Order(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    address = models.CharField(max_length=100, default='', blank=True)
    phone = models.CharField(max_length=20, default='', blank=True)
    date = models.DateField(default=datetime.datetime.today)
    status = models.BooleanField(default=False)
    
    def __str__(self):
        return self.product
    
    
class NewsletterSubscriber(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(max_length=100, unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.email
    

# columns:full_name,email,phone_number, order_number, subject and message
class Message(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)
    order_number = models.CharField(max_length=50, blank=True, null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Message from {self.full_name} - {self.subject}"