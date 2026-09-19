from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.db.models import Q
import logging
import json
import os
from dotenv import load_dotenv
from cart.cart import Cart

from .services.email import EmailService
from .models import Product, Category, Profile, Customer, NewsletterSubscriber, Message
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
from payment.forms import ShippingForm
from payment.models import ShippingAddress, Order

load_dotenv()  # Load environment variables from .env file

logger = logging.getLogger(__name__)

api_key = os.getenv('SENDGRID_API_KEY')

email_service = EmailService(api_key=api_key)

# Create your views here.

def home(request):
    products = Product.objects.all()[:12]
    
    context = {
        "products":products,
    }
    
    return render(request, "home.html", context)


def about(request):
    
    return render(request, "about.html", {})

def contact(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone_number = request.POST.get("phone_number")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        if not full_name or not email or not phone_number or not subject or not message:
            messages.error(request, "Fill the missing fields!")
            return redirect("contact")

        order = None
        order_number = None

        if request.user.is_authenticated:
            order = (
                Order.objects
                .filter(user=request.user)
                .order_by("-date_ordered")
                .first()
            )

            if order:
                order_number = order.id

        data = Message(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            order_number=order_number,
            subject=subject,
            message=message
        )

        data.save()

        messages.success(
            request,
            "Message has been sent to SokoHub Support successfully."
        )

        return redirect("contact")

    return render(request, "contact.html")
        
    
    

def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Cart shopping 
            current_user = Profile.objects.get(user__id=request.user.id)
            
            # Get their saved cart from database
            saved_cart = current_user.old_cart
            # Convert database String to python dictionary
            if saved_cart:
                # Convert to dictionary using json
                converted_cart = json.loads(saved_cart)
                
                # Add the loaded cart_dict to the session
                # Get cart
                cart = Cart(request)
                
                # Now looping through the cart and add products from the database
                for key, value in converted_cart.items():
                    cart.db_add(product=key, quantity=value)
                    
            
            
            messages.success(request, ("Logged in successfully."))
            return redirect("home")
        
        else:
            messages.error(request, ("Incorrect username or password, please try again!"))
            return redirect("login")
    else:
                        
        return render(request, "login.html", {})

def logout_user(request):
    logout(request)
    
    messages.success(request, ("Logout successsfully!"))
    return redirect("home")


def register_user(request):
    try:
        form = SignUpForm()
        if request.method == "POST":
            form = SignUpForm(request.POST)
            if form.is_valid():
                form.save()
                username = form.cleaned_data.get("username")
                password = form.cleaned_data.get("password1")
                
                user = authenticate(username=username, password=password)
                login(request, user)
                
                messages.success(request, ("Account created successfully."))
                return redirect("update_info")
            
            else:
                print(form.errors)
                messages.error(request, (form.errors))
                return redirect("register")
        
        else:
            return render(request, "register.html", {"form":form})
    
    except Exception as e:
        logger.error(f"Error occured: {e}")
        print(f"failed {e}")        
                

def product(request, pk):
    product = Product.objects.get(id=pk)
    
    return render(request, "product.html", {"product":product})


def category(request, foo):
    # Replacing - to whitespace in foo variable
    foo = foo.replace("-", "")
    try:
        category = Category.objects.get(name=foo)
        products = Product.objects.filter(category=category)
        
        return render(request, "category.html", {"products":products,"category":category})
          
    except:
        messages.error(request, ("Category does not exist"))
        return redirect("home")
    

def category_summary(request):
    categories = Category.objects.all()
    products = Product.objects.all()

    
    
    return render(request, "category_summary.html", {"categories":categories, "products":products})


def update_user(request):
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        user_form = UpdateUserForm(request.POST or None, instance=current_user)
        
        if user_form.is_valid():
            user_form.save()
            login(request, current_user)
            
            messages.success(request, ("User has been updated."))
            
            return redirect("home")
        return render(request, "update_user.html", {"user_form":user_form})
    
    else:
        messages.error(request, ("You must be logged in to access profile"))
        
        return redirect("home")
    


def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user
        
        if request.method == "POST":
            form = ChangePasswordForm(current_user,request.POST)
            
            if form.is_valid():
                form.save()
                messages.success(request, ("Your password has been updated successfully."))
                #login(request, current_user)
                
                return redirect("login")
            
            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)
        
        
        form = ChangePasswordForm(current_user)
            
        return render(request, "update_password.html", {"form":form})
    
    else:
        messages.error(request, ("You must be logged in to access the page"))
        
        return redirect("home")
    
    

def update_info(request):
    if request.user.is_authenticated:
        # Get current user        
        current_user = Profile.objects.get(user__id=request.user.id)
        # Get current user Shipping info
        shipping_user = ShippingAddress.objects.get(user=request.user)
        
        # Get original user form        
        form = UserInfoForm(request.POST or None, instance=current_user)
        # Get shipping form
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        
        if form.is_valid() and shipping_form.is_valid():
            # Saving original form
            form.save()
            
            # Saving Shipping form
            shipping_form.save()
            print(f"{shipping_user} has been saved")
            print(f"{shipping_user} has been saved")
            
            messages.success(request, ("User Info has been updated."))
            
            return redirect("home")
        return render(request, "update_info.html", {"form":form, "shipping_form":shipping_form})
            
    else:
        messages.error(request, ("You must be logged in to access profile"))
        
        return redirect("home")
    
    
    
def search(request):
    #Determine if they filled the form
    if request.method == "POST":
        searched = request.POST.get("searched") 
        
        # Quering the Products database model
        searched = Product.objects.filter(Q(name__icontains=searched) | Q(description__icontains=searched))
        
        if not searched:
            messages.error(request, ("Product does not exist!")) 
            
            return render(request, "search.html", {})
    
        return render(request, "search.html", {"searched":searched})
    
    else:
        return render(request, "search.html", {})
    
    
    
def newsletter_subscribe(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        print(f"Received newsletter subscription request for email: {email}")

        existing_subscriber = NewsletterSubscriber.objects.filter(
            email=email
        ).first()

        if not existing_subscriber:
            subscriber = NewsletterSubscriber.objects.create(
                email=email,
                customer=request.user if request.user.is_authenticated else None
            )

            first_name = (
                subscriber.customer.first_name
                if subscriber.customer
                else "Customer"
            )

            subject = "Welcome to SokoHub!"

            message = (
                f"Hello {first_name},\n\n"
                "Thank you for subscribing to the SokoHub newsletter! "
                "We're excited to have you on board. You'll receive "
                "updates about new arrivals, exclusive deals, and "
                "special offers.\n\n"
                "Best regards,\n"
                "SokoHub Team"
            )

            response = email_service.send_email(
                from_email=os.getenv("SENDGRID_FROM_EMAIL"),
                to_email=email,
                subject=subject,
                content=message
            )

            if response:
                print(f"Sent welcome email to {email}")
                
                messages.success(request,
                    "Thank you for subscribing to our newsletter! "
                    "A welcome email has been sent to your inbox."
                )
                
            else:
                print(f"Failed to send welcome email to {email}")
                
                messages.error(request,
                    "There was an issue sending the welcome email. "
                    "Please check your email address and try again."
                )

           

        elif existing_subscriber.is_active:
            messages.info(
                request,
                "You are already subscribed to our newsletter."
            )

        else:
            existing_subscriber.is_active = True

            # Attach the account if they are logged in
            if request.user.is_authenticated:
                existing_subscriber.customer = request.user

            existing_subscriber.save()

            messages.success(
                request,
                "Your subscription has been reactivated."
            )

        return redirect("home")

    return redirect("home")