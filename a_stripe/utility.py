import stripe

def get_product_details(product):
    prices = stripe.Price.list(product = product['id'])
    price = prices['data'][0]
    product_details = {
        'id' : product['id'],
        'name' : product['name'],
        'image' : product['images'][0],
        'description' : product['description'],
        'price' : price['unit_amount'] / 100,
    }
    return product_details
"""
from decimal import Decimal

DEFAULT_IMAGE = "/static/no-image.png"

def get_product_details(product):
    product_id = product.get('id')
    name = product.get('name', 'Untitled')
    images = product.get('images') or []
    image = images[0] if images else DEFAULT_IMAGE

    # Try to fetch prices and handle empty list
    try:
        prices = stripe.Price.list(product=product_id)
    except Exception as e:
        print(f"Error fetching prices for product {product_id}: {e}")
        prices = {}

    price_obj = None
    if prices and prices.get('data'):
        price_obj = prices['data'][0]
        print(f"  Price found for {product_id}: {price_obj.get('id')} unit_amount={price_obj.get('unit_amount')} currency={price_obj.get('currency')}")
    else:
        print(f"  No prices for product {product_id}")

    unit_amount = price_obj.get('unit_amount') if price_obj else None
    price_display = (Decimal(unit_amount) / Decimal(100)) if unit_amount is not None else None

    product_details = {
        'id': product_id,
        'name': name,
        'image': image,
        'description': product.get('description', ''),
        'price': price_display,
        'currency': price_obj.get('currency') if price_obj else None,
        'raw_price_obj': price_obj,
    }
    return product_details
"""