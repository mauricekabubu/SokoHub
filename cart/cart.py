from store.models import Product, Profile

class Cart():
    def __init__(self, request):
        self.session = request.session
        self.request = request
        
        #Get the current session key if it exists 
        cart = self.session.get("session_key")
        
        # if on session key exists lets create one
        if "session_key" not in request.session:
            cart = self.session["session_key"]= {}
            
        
        # Make sure the cart is available on all sites of the pages
        self.cart = cart
        
    def db_add(self, product, quantity):
        product_id = str(product)
        product_qty = str(quantity)
        
        if product_id in self.cart:
            pass
        else:
            #self.cart[product_id] = {"product_price": str(product.price)}
            self.cart[product_id] = int(product_qty)
            
        self.session.modified = True
        
        # deal with logged in user
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # converting the cart dict into a string
            carty = str(self.cart)
            carty = carty.replace("\'","\"")
            
            #save carty to the profile model
            current_user.update(old_cart=str(carty))
        
        
    def add(self, product, quantity):
        product_id = str(product.id)
        product_qty = str(quantity)
        
        if product_id in self.cart:
            pass
        else:
            #self.cart[product_id] = {"product_price": str(product.price)}
            self.cart[product_id] = int(product_qty)
            
        self.session.modified = True
        
        # deal with logged in user
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # converting the cart dict into a string
            carty = str(self.cart)
            carty = carty.replace("\'","\"")
            
            #save carty to the profile model
            current_user.update(old_cart=str(carty))
            
        
    def __len__(self):
        return len(self.cart)
        
        
    def get_prods(self):
        # Get the ids from the cart
        product_ids = self.cart.keys()
        
        # Use the ids to lookup the products from database
        products = Product.objects.filter(id__in=product_ids)
        
        #Return those looked up products
        return products
    
    def get_quants(self):
        quantities = self.cart
        
        return quantities
    
    def update(self, product_id, quantity):
        # Cart structure: {"4": 3}
        # Product ID  -> quantity

        product_id = str(product_id)
        product_qty = int(quantity)

        self.cart[product_id] = product_qty
        self.session.modified = True
        
        # deal with logged in user
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # converting the cart dict into a string
            carty = str(self.cart)
            carty = carty.replace("\'","\"")
            
            #save carty to the profile model
            current_user.update(old_cart=str(carty))
                    

        return self.cart
    
    
    def delete(self, product):
        print("1. DELETE PRODUCT:", product)

        product_id = str(product)
        print("2. PRODUCT ID:", product_id)

        print("3. CART:", self.cart)

        if product_id in self.cart:
            print("4. PRODUCT EXISTS")
            del self.cart[product_id]
            print("5. PRODUCT DELETED")
        else:
            print("4. PRODUCT DOES NOT EXIST")

        print("6. ABOUT TO MODIFY SESSION")

        self.session.modified = True

        print("7. SESSION MODIFIED")
        # deal with logged in user
        if self.request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # converting the cart dict into a string
            carty = str(self.cart)
            carty = carty.replace("\'","\"")
            
            #save carty to the profile model
            current_user.update(old_cart=str(carty))
                    
        
    def cart_total(self):
        #Get product_ids 
        product_ids = self.cart.keys()
        
        #Lookup up those keys in our products in product database model
        products = Product.objects.filter(id__in=product_ids)
        
        #Get quantities 
        quantities = self.cart
        
        total = 0
        for key, value in quantities.items():
            #convert key string into integer key-->{"4":2} 4=key and 2=value
            key = int(key)
            for product in products:
                if product.id == key:
                    total = total + (product.price*value)
            
        return total
        