from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
import logging

from .cart import Cart
from store.models import Product


#create a logger 
logger = logging.getLogger(__name__)

# Create your views here.
def cart_summary(request):
    # Get the cart
    cart = Cart(request)
    print("CART SESSION:", cart.cart)
    cart_products = cart.get_prods  
    quantities = cart.get_quants 
    totals = cart.cart_total()
    
    return render(request, "cart_summary.html", {"cart_products":cart_products, "quantities":quantities,"totals":totals})

def cart_add(request):
    cart = Cart(request)

    if request.method == "POST":
        try:
            product_id = int(request.POST.get("product_id"))
            product_qty = int(request.POST.get("product_qty"))

            product = get_object_or_404(Product, id=product_id)

            cart.add(product=product, quantity=product_qty)
            
            # Get cart quantity
            cart_quantity = cart.__len__()
            
            messages.success(request, ("Product added successfully"))
            
            
            return JsonResponse(
                {
                    "qty":cart_quantity
                }
            )

        except Exception as e:
            logger.error(f"Error occurred: {e}")
            print(e)

            return JsonResponse({
                "error": str(e)
            }, status=400)

    return JsonResponse({
        "error": "POST request required"
    }, status=405)
    
    
    
def cart_delete(request):
    cart = Cart(request)
    if request.method == "POST":
        try:
            product_id = int(request.POST.get("product_id"))
            
            cart.delete(product=product_id)
            
            messages.success(request, ("Product deleted successfully"))
            
            return JsonResponse(
                {
                    "product":product_id
                }
            )
            
            
        except Exception as e:
                    logger.error(f"Error occurred: {e}")
                    print(e)
        
                    return JsonResponse({
                        "error": str(e)
                    }, status=400)
        
    return JsonResponse({
        "error": "POST request required"
    }, status=405)
    
     

def cart_update(request):
    cart = Cart(request)
    if request.method == "POST":
        try:
            product_id = int(request.POST.get("product_id"))
            product_qty = int(request.POST.get("product_qty"))

            cart.update(product_id=product_id, quantity=product_qty)
            
            # Get cart quantity
            #cart_quantity = cart.__len__()
            
            messages.success(request, ("Product updated successfully"))
            
            
            return JsonResponse(
                {
                    "qty":product_qty
                }
            )

        except Exception as e:
            logger.error(f"Error occurred: {e}")
            print(e)

            return JsonResponse({
                "error": str(e)
            }, status=400)

    return JsonResponse({
        "error": "POST request required"
    }, status=405)


