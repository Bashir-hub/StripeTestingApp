from .cart import Cart
from django.shortcuts import redirect


def cart(request):
    cart = Cart(request)
    return { 'cart' : cart} 