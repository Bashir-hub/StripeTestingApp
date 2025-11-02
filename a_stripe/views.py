from django.shortcuts import render,redirect,reverse
import stripe 
import traceback
from django.conf import settings 
from .models import *
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse,  HttpResponseBadRequest, HttpResponseServerError
from django.contrib.auth import get_user_model
from .utility import *
from .cart import Cart 




stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.

def shop_view(request):
    products_list = stripe.Product.list()
    print("STRIPE PRODUCTS COUNT:", len(products_list.get('data', [])))
    products = []

    for product in products_list['data']:
        if product.get('metadata',{}).get('category')=="shop":
           products.append(get_product_details(product))     
    return render(request,'a_stripe/shop.html', {'products' : products})

def product_view(request, product_id):
    product = stripe.Product.retrieve(product_id)
    product_details = get_product_details(product)
    
    cart = Cart(request)
    product_details['in_cart'] = product_id in cart.cart_session
    return render(request, 'a_stripe/product.html',{'product' : product_details})

def add_to_cart(request,  product_id):
    cart = Cart(request)
    cart.add(product_id)
    print(cart.cart_session)

    product = stripe.Product.retrieve(product_id)
    product_details = get_product_details(product)
    product_details['in_cart']= product_id in cart.cart_session

    response =  render(request, 'a_stripe/partials/cart-button.html',{'product': product_details})
    response['HX-Trigger'] = 'hx_menu_cart'
    return response


def hx_menu_cart(request):
    return render(request,'a_stripe/partials/menu-cart.html')

def cart_view(request):
    quantity_range=list(range(1, 11))
    return render(request, 'a_stripe/cart.html', {'quantity_range' : quantity_range})

def update_checkout(request,product_id):
    quantity = int(request.POST.get('quantity', 1))
    cart = Cart(request)
    cart.add(product_id, quantity)

    product= stripe.Product.retrieve(product_id)
    product_details = get_product_details(product)
    product_details['total_price']= product_details['price'] * quantity 

    response = render(request, 'a_stripe/partials/checkout-total.html', {'product_details' : product_details })
    response['HX-Trigger'] = 'hx_menu_cart'
    return response

def remove_from_cart_view(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    return redirect('cart')


User = get_user_model()
def payment_successful(request):
    customer = None
    checkout_session_id = request.GET.get('session_id', None)

    if not checkout_session_id:
        # No session id provided
        return render(request, 'a_stripe/payment_successful.html', {'customer': None})

    try:
        session = stripe.checkout.Session.retrieve(checkout_session_id)
    except Exception as e:
        print("Error retrieving checkout session:", e)
        print(traceback.format_exc())
        return render(request, 'a_stripe/payment_successful.html', {'customer': None})

    # Try to get customer object (may be a customer id)
    customer_id = session.get('customer')
    try:
        if customer_id:
            customer = stripe.Customer.retrieve(customer_id)
        else:
            customer = None
    except Exception as e:
        print("Error retrieving stripe customer:", e)
        print(traceback.format_exc())
        customer = None

    # Safely get the first line item (if any)
    try:
        line_items = stripe.checkout.Session.list_line_items(checkout_session_id).data
        if not line_items:
            line_item = None
        else:
            line_item = line_items[0]
    except Exception as e:
        print("Error fetching line items:", e)
        print(traceback.format_exc())
        line_item = None

    # Determine a user to attach the payment to:
    # Prefer logged-in user, then session metadata.user_id, then customer email lookup
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        # Try metadata first (recommended to set metadata={'user_id': user.id} when creating the session)
        metadata = session.get('metadata') or {}
        user_id = metadata.get('user_id')
        if user_id:
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                user = None
        # Fallback: try customer email
        if not user:
            customer_details = session.get('customer_details') or {}
            email = customer_details.get('email')
            if email:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = None

    # Build defaults for create
    defaults = {
        'user': user,
        'stripe_customer_id': customer_id,
        'stripe_product_id': getattr(line_item.price, 'product', None) if line_item else None,
        'product_name': getattr(line_item, 'description', None) if line_item else None,
        'quantity': getattr(line_item, 'quantity', 0) if line_item else 0,
        'price': (getattr(line_item.price, 'unit_amount', 0) / 100.0) if (line_item and getattr(line_item, 'price', None)) else 0.0,
        'currency': getattr(line_item.price, 'currency', None) if (line_item and getattr(line_item, 'price', None)) else None,
        'has_paid': True,
    }

    try:
        UserPayment.objects.update_or_create(
                    stripe_checkout_id=checkout_session_id,
                     defaults={
                        'user': user,
                        'stripe_customer_id': customer_id,
                        'stripe_product_id': getattr(line_item.price, 'product', None) if line_item else None,
                        'product_name': getattr(line_item, 'description', None) if line_item else None,
                        'quantity': getattr(line_item, 'quantity', 0) if line_item else 0,
                        'price': (getattr(line_item.price, 'unit_amount', 0) / 100.0) if (line_item and getattr(line_item, 'price', None)) else 0.0,
                        'currency': getattr(line_item.price, 'currency', None) if (line_item and getattr(line_item, 'price', None)) else None,
                        'has_paid': True
                    }
                )
    except Exception as e:
            print("Error creating/updating UserPayment:", e)
            print(traceback.format_exc())
    return render(request, 'a_stripe/payment_successful.html', {'customer': customer})
"""
def payment_successful(request):

    checkout_session_id = request.GET.get('session_id', None)

    if checkout_session_id:
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        customer_id = session.customer
        customer = stripe.Customer.retrieve(customer_id)
        # inject this customer in to the success template and
        #  keep this record in the database
        line_item = stripe.checkout.Session.list_line_items(checkout_session_id).data[0]
        UserPayment.objects.get_or_create(
            user = request.user,
            stripe_customer_id = customer_id,
            stripe_checkout_id = checkout_session_id,
            stripe_product_id = line_item.price.product,
            product_name = line_item.description,
            quantity = line_item.quantity,
            price = line_item.price.unit_amount/100.0,
            currency = line_item.price.currency,
            has_paid = True
        )
    return render(request, 'a_stripe/payment_successful.html', {'customer':customer})
"""
def payment_cancelled(request):
    return render(request, 'a_stripe/payment_successful.html')

@require_POST
@csrf_exempt
def stripe_webhook(request):
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    print("=== STRIPE WEBHOOK HIT ===")
    print("Payload length:", len(payload))
    print("Sig header (start):", sig_header[:200])
    print("Endpoint secret set?:", bool(endpoint_secret))

    if not endpoint_secret:
        print("ERROR: STRIPE_WEBHOOK_SECRET not set in settings.")
        return HttpResponseServerError("Webhook signing secret not configured.")

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=endpoint_secret)
    except ValueError as e:
        print("Invalid payload:", e)
        print(traceback.format_exc())
        return HttpResponseBadRequest("Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print("Signature verification failed:", e)
        print("Sig header (start):", sig_header[:200])
        print(traceback.format_exc())
        return HttpResponseBadRequest("Invalid signature")
    except Exception as e:
        print("Unexpected error during construct_event:", e)
        print(traceback.format_exc())
        return HttpResponseServerError("Webhook verification error")

    try:
        event_type = event.get("type")
        print("Received Stripe event:", event_type)

        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            checkout_session_id = session.get("id")
            print("checkout_session_id:", checkout_session_id)

            try:
                user_payment = UserPayment.objects.get(stripe_checkout_id=checkout_session_id)
            except UserPayment.DoesNotExist:
                print(f"No UserPayment found for checkout id: {checkout_session_id}")
                return HttpResponse(status=200)

            user_payment.has_paid = True
            user_payment.save()
            print(f"Marked payment as paid for checkout id: {checkout_session_id}")

    except Exception as e:
        print("Error processing webhook event:", e)
        print(traceback.format_exc())
        return HttpResponseServerError("Error processing webhook")

    return HttpResponse(status=200)
"""
@require_POST
@csrf_exempt
def stripe_webhook(request):
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    payload = request.body
    signature_header = request.META['HTTP_STRIPE_SIGNATURE','']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, signature_header, endpoint_secret
        )
    except:
        return HttpResponse(status = 400)
    
    if event['type'] == 'checkout.session.completed':
       session = event['data']['object']
       checkout_session_id = session.get('id')
       user_payment = UserPayment.objects.get(stripe_checkout_id=checkout_session_id)
       user_payment.has_paid = True
       user_payment.save()
    return HttpResponse(status = 200) # means it is ok he has paid 
"""