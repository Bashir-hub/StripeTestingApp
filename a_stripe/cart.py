import stripe 
from django.conf import settings 
from.utility import *

stripe.api_key = settings.STRIPE_SECRET_KEY

class Cart:
    def __init__(self,request):
        self.session = request.session                             # assigning a session to the request of the user
        cart_session = self.session.get(settings.CART_SESSION_ID) # assigning the cart session 
       
        if not cart_session:
            self.session[settings.CART_SESSION_ID] = {}
            cart_session = self.session[settings.CART_SESSION_ID]                        # making the cart session available throughout 
        self.cart_session = cart_session

    def __iter__(self):     # use in python when you want loop and return a list of quantity 
        for product_id, item in self.cart_session.items():
            product = stripe.Product.retrieve(product_id)
            product_details=get_product_details(product)

            yield {                  #yield is similar to append but instead to append all the object at once it will return only one object. it is mainly used when dealing with the large dataset 
                'id' : product_id,  
                'image' : product_details['image'],
                'name' : product_details['name'],
                'price' : product_details['price'],
                'quantity' : item['quantity'],
                'total_price' : product_details['price'] * item['quantity'],
            }
    def __len__(self):          # tell the number of items in the cart session 
        return sum(item.get('quantity',0) for item in self.cart_session.values()) # return the total no. item
    
    def save(self): #which tells the gloval that something is modified so it has to be save 
        self.session.modified = True
    
    def add(self, product_id, quantity=1):
        self.cart_session[product_id] = {
            'quantity' : quantity,
        } 
        self.save()
    

    def remove(self, product_id):
        if product_id in self.cart_session:
            del self.cart_session[product_id]
            self.save()
    def get_total_cost(self):
        return sum(product_item['total_price'] for product_item in self)
