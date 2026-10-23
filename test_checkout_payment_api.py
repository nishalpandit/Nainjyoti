import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from decimal import Decimal
from nainjyoti.models import (
    Category, VendorProfile, UserProfile, UserAddress,
    Product, ProductVariant, CartItem, Order, OrderItem,
    PaymentTransaction, StockLog, OrderStatusHistory
)

def run_tests():
    client = Client()
    print("=" * 70)
    print("STARTING CHECKOUT & PAYMENT API TEST SUITE")
    print("=" * 70)

    # 1. Setup Test Data
    # -------------------------------------------------------------
    customer_user, _ = User.objects.get_or_create(username='test_customer_checkout')
    customer = UserProfile.objects.filter(phone='9999988888').first()
    if not customer:
        customer = UserProfile.objects.create(
            user=customer_user,
            phone='9999988888',
            first_name='Test Checkout',
            last_name='Customer',
            email='checkout@test.com',
            auth_token='test_token_checkout_123',
            is_active=True,
        )
    customer.auth_token = 'test_token_checkout_123'
    customer.is_active = True
    customer.save()

    vendor_user, _ = User.objects.get_or_create(username='test_vendor_checkout')
    vendor, _ = VendorProfile.objects.get_or_create(
        user=vendor_user,
        defaults={
            'business_name': 'SuperTech Electronics',
            'owner_name': 'Ramesh Kumar',
            'phone': '9123456780',
            'vendor_code': 'VEND-CHK-01',
            'status': 'APPROVED',
        }
    )
    vendor.status = 'APPROVED'
    vendor.save()

    cat, _ = Category.objects.get_or_create(
        name='Consumer Electronics',
        defaults={'status': 'ACTIVE', 'description': 'Electronics products'}
    )
    cat.status = 'ACTIVE'
    cat.save()

    # Product with variant
    prod_var, _ = Product.objects.get_or_create(
        sku='SKU-PHONE-X1',
        defaults={
            'name': 'Flagship Smartphone Pro',
            'category': cat,
            'vendor': vendor,
            'price': Decimal('49999.00'),
            'stock_quantity': 50,
            'status': 'ACTIVE',
            'is_approved': True,
        }
    )
    prod_var.status = 'ACTIVE'
    prod_var.is_approved = True
    prod_var.save()

    variant, _ = ProductVariant.objects.get_or_create(
        sku='SKU-PHONE-X1-BLK',
        defaults={
            'product': prod_var,
            'title': 'Space Black 256GB',
            'color': 'Black',
            'size': '256GB',
            'price': Decimal('49999.00'),
            'discount_price': Decimal('46999.00'),
            'stock_quantity': 10,
            'is_active': True,
        }
    )
    variant.stock_quantity = 10
    variant.is_active = True
    variant.save()

    # Product without variant
    prod_single, _ = Product.objects.get_or_create(
        sku='SKU-CHARGER-65W',
        defaults={
            'name': '65W Fast GaN Charger',
            'category': cat,
            'vendor': vendor,
            'price': Decimal('1999.00'),
            'discount_price': Decimal('1499.00'),
            'stock_quantity': 20,
            'status': 'ACTIVE',
            'is_approved': True,
        }
    )
    prod_single.stock_quantity = 20
    prod_single.status = 'ACTIVE'
    prod_single.is_approved = True
    prod_single.save()

    # Address
    address, _ = UserAddress.objects.get_or_create(
        user=customer,
        defaults={
            'full_name': 'Test Checkout Customer',
            'phone': '9876543210',
            'address_line_1': 'Plot 42, Silicon Valley Road',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'pincode': '560100',
            'country': 'India',
            'is_default': True,
        }
    )

    auth_headers = {'HTTP_AUTHORIZATION': f'Bearer {customer.auth_token}'}

    # 2. Test Cart Operations
    # -------------------------------------------------------------
    CartItem.objects.filter(user=customer).delete()

    # Add variant to cart
    res = client.post(
        '/api/user/cart/add/',
        data=json.dumps({'product_id': prod_var.id, 'variant_id': variant.id, 'quantity': 1}),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code in [200, 201], f"Cart add variant failed: {res.content}"
    data = res.json()
    assert data['success'] is True
    print("PASS: Add variant item to cart")

    # Add single product to cart
    res = client.post(
        '/api/user/cart/add/',
        data=json.dumps({'product_id': prod_single.id, 'quantity': 2}),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code in [200, 201], f"Cart add single product failed: {res.content}"
    print("PASS: Add standalone product to cart")

    # List cart
    res = client.get('/api/user/cart/', **auth_headers)
    assert res.status_code == 200
    cart_data = res.json()['cart']
    assert cart_data['item_count'] == 2
    assert cart_data['total_quantity'] == 3
    # variant (46999 * 1) + single (1499 * 2) = 46999 + 2998 = 49997
    assert cart_data['total'] == 49997.0
    print(f"PASS: Cart listing verified (Total: Rs.{cart_data['total']})")

    # 3. Test Checkout with COD
    # -------------------------------------------------------------
    var_stock_before = ProductVariant.objects.get(id=variant.id).stock_quantity
    single_stock_before = Product.objects.get(id=prod_single.id).stock_quantity

    res = client.post(
        '/api/user/checkout/',
        data=json.dumps({'address_id': address.id, 'payment_method': 'COD'}),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code == 201, f"Checkout COD failed: {res.content}"
    checkout_res = res.json()
    assert checkout_res['success'] is True
    assert checkout_res['cart_cleared'] is True
    order_data = checkout_res['order']
    payment_data = checkout_res['payment']

    assert order_data['payment_method'] == 'COD'
    assert order_data['payment_status'] == 'PENDING'
    assert order_data['total_amount'] == 49997.0
    assert payment_data['method'] == 'COD'
    assert payment_data['status'] == 'PENDING'

    # Check cart is now empty
    assert CartItem.objects.filter(user=customer).count() == 0

    # Check atomic stock deduction
    var_stock_after = ProductVariant.objects.get(id=variant.id).stock_quantity
    single_stock_after = Product.objects.get(id=prod_single.id).stock_quantity
    assert var_stock_after == var_stock_before - 1
    assert single_stock_after == single_stock_before - 2

    # Check stock logs
    assert StockLog.objects.filter(reference_id=order_data['order_number']).count() == 2

    print(f"PASS: Checkout COD completed successfully (Order: {order_data['order_number']})")
    print(f"      Stock deducted: Variant {var_stock_before} -> {var_stock_after}, Product {single_stock_before} -> {single_stock_after}")

    # 4. Test Checkout with ONLINE Payment
    # -------------------------------------------------------------
    # Add item to cart again
    client.post(
        '/api/user/cart/add/',
        data=json.dumps({'product_id': prod_single.id, 'quantity': 1}),
        content_type='application/json',
        **auth_headers
    )

    res = client.post(
        '/api/user/checkout/',
        data=json.dumps({
            'address_id': address.id,
            'payment_method': 'ONLINE',
            'provider': 'RAZORPAY'
        }),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code == 201, f"Checkout ONLINE failed: {res.content}"
    online_res = res.json()
    assert online_res['success'] is True
    order_online = online_res['order']
    payment_online = online_res['payment']

    assert order_online['payment_method'] == 'ONLINE'
    assert order_online['payment_status'] == 'PENDING'
    assert payment_online['method'] == 'ONLINE'
    assert payment_online['status'] == 'INITIATED'
    assert payment_online['provider'] == 'RAZORPAY'
    assert online_res['payment_instructions']['action_required'] is True
    print(f"PASS: Checkout ONLINE created (Ref: {payment_online['reference']}, Provider: {payment_online['provider']})")

    # 5. Test Payment Verification
    # -------------------------------------------------------------
    verify_payload = {
        'payment_reference': payment_online['reference'],
        'status': 'PAID',
        'provider': 'RAZORPAY',
        'provider_payment_id': 'pay_test_987654321',
        'provider_order_id': 'order_test_123456',
    }
    res = client.post(
        '/api/user/payment/verify/',
        data=json.dumps(verify_payload),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code == 200, f"Payment verify failed: {res.content}"
    verify_res = res.json()
    assert verify_res['success'] is True
    assert verify_res['payment']['status'] == 'PAID'
    assert verify_res['order']['payment_status'] == 'PAID'
    assert verify_res['payment']['provider_payment_id'] == 'pay_test_987654321'
    print(f"PASS: Online payment verified successfully as PAID")

    # Check payment status lookup
    res = client.get(f"/api/user/payment/status/{payment_online['reference']}/", **auth_headers)
    assert res.status_code == 200
    status_data = res.json()
    assert status_data['payment']['status'] == 'PAID'
    print("PASS: Payment status lookup by reference verified")

    # 6. Test Customer Orders List & Detail
    # -------------------------------------------------------------
    res = client.get('/api/user/orders/', **auth_headers)
    assert res.status_code == 200
    orders_list = res.json()['orders']
    assert len(orders_list) >= 2
    print(f"PASS: Customer order history list verified ({len(orders_list)} orders)")

    res = client.get(f"/api/user/orders/{order_online['id']}/", **auth_headers)
    assert res.status_code == 200
    order_detail = res.json()['order']
    assert order_detail['id'] == order_online['id']
    assert 'timeline' in order_detail
    assert len(order_detail['timeline']) >= 2  # Created + Payment verified
    print("PASS: Customer order detail and status timeline verified")

    # 7. Test Edge Cases & Validations
    # -------------------------------------------------------------
    # Empty cart checkout
    res = client.post(
        '/api/user/checkout/',
        data=json.dumps({'address_id': address.id, 'payment_method': 'COD'}),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code == 400
    assert 'empty' in res.json()['message'].lower()
    print("PASS: Empty cart checkout rejected with 400")

    # Invalid address
    client.post(
        '/api/user/cart/add/',
        data=json.dumps({'product_id': prod_single.id, 'quantity': 1}),
        content_type='application/json',
        **auth_headers
    )
    res = client.post(
        '/api/user/checkout/',
        data=json.dumps({'address_id': 999999, 'payment_method': 'COD'}),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code == 404
    print("PASS: Invalid address ID rejected with 404")

    # Invalid payment method
    res = client.post(
        '/api/user/checkout/',
        data=json.dumps({'address_id': address.id, 'payment_method': 'BITCOIN'}),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code == 400
    print("PASS: Invalid payment method rejected with 400")

    # Insufficient stock validation
    variant.stock_quantity = 1
    variant.save()
    client.post(
        '/api/user/cart/add/',
        data=json.dumps({'product_id': prod_var.id, 'variant_id': variant.id, 'quantity': 1}),
        content_type='application/json',
        **auth_headers
    )
    # Now artificially drop stock to 0 before checkout
    variant.stock_quantity = 0
    variant.save()
    res = client.post(
        '/api/user/checkout/',
        data=json.dumps({'address_id': address.id, 'payment_method': 'COD'}),
        content_type='application/json',
        **auth_headers
    )
    assert res.status_code == 400
    assert 'available' in res.json()['message'].lower()
    print("PASS: Insufficient stock detected during checkout and rejected with 400")

    print("=" * 70)
    print("ALL CHECKOUT & PAYMENT API TESTS PASSED SUCCESSFULLY (100%!)")
    print("=" * 70)

if __name__ == '__main__':
    run_tests()
