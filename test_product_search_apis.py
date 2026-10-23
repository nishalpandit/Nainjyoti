import os
import sys
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from nainjyoti.models import Category, Product, VendorProfile

def run_tests():
    print("=" * 60)
    print("RUNNING STEP 6: PRODUCT SEARCH API TESTS")
    print("=" * 60)

    client = Client()

    # Setup Test Data
    Category.objects.filter(name__in=["Search Cat A", "Search Cat B"]).delete()
    VendorProfile.objects.filter(vendor_code__in=["VEND-SRCH1", "VEND-SRCH2"]).delete()
    User.objects.filter(username__in=["usr_srch_1", "usr_srch_2"]).delete()

    cat_a = Category.objects.create(name="Search Cat A", status="ACTIVE")
    cat_b = Category.objects.create(name="Search Cat B", status="ACTIVE")

    # Approved Vendor
    u1 = User.objects.create_user(username="usr_srch_1")
    v1 = VendorProfile.objects.create(
        user=u1,
        vendor_code="VEND-SRCH1",
        business_name="Apex Fashion Hub",
        owner_name="Apex Owner",
        phone="9111222333",
        status="APPROVED"
    )

    # Pending / Unapproved Vendor
    u2 = User.objects.create_user(username="usr_srch_2")
    v2 = VendorProfile.objects.create(
        user=u2,
        vendor_code="VEND-SRCH2",
        business_name="Unapproved Store",
        owner_name="Pending Owner",
        phone="9444555666",
        status="PENDING"
    )

    # Products
    p1 = Product.objects.create(
        vendor=v1,
        category=cat_a,
        name="Cotton Casual Denim Shirt",
        sku="SKU-SHIRT-01",
        description="Blue slim fit denim cotton shirt",
        price=Decimal("1200.00"),
        discount_price=Decimal("999.00"),
        stock_quantity=15,
        status="ACTIVE",
        is_approved=True
    )
    p2 = Product.objects.create(
        vendor=v1,
        category=cat_a,
        name="Linen White Formal Shirt",
        sku="SKU-SHIRT-02",
        description="Breathable pure linen shirt for office",
        price=Decimal("1800.00"),
        discount_price=None,
        stock_quantity=0,  # Out of stock
        status="ACTIVE",
        is_approved=True
    )
    p3 = Product.objects.create(
        vendor=v1,
        category=cat_b,
        name="Leather Strap Classic Watch",
        sku="SKU-WATCH-01",
        description="Waterproof luxury analog timepiece",
        price=Decimal("3500.00"),
        discount_price=Decimal("2999.00"),
        stock_quantity=8,
        status="ACTIVE",
        is_approved=True
    )
    # Product from unapproved vendor (should not appear in search)
    p4 = Product.objects.create(
        vendor=v2,
        category=cat_a,
        name="Black Cotton Shirt",
        sku="SKU-SHIRT-04",
        description="Shirt from unapproved vendor",
        price=Decimal("799.00"),
        stock_quantity=10,
        status="ACTIVE",
        is_approved=True
    )

    print("[PASS] Test fixtures created successfully")

    # Test 1: Search by keyword 'shirt'
    res = client.get('/api/user/products/search/?q=shirt')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data['success'] is True
    assert data['total_matches'] == 2  # p1 and p2 (p4 excluded because vendor is PENDING)
    names = [p['name'] for p in data['products']]
    assert "Cotton Casual Denim Shirt" in names
    assert "Linen White Formal Shirt" in names
    assert "Black Cotton Shirt" not in names
    print(f"[PASS] Test 1: Search by 'shirt' matched {data['total_matches']} approved products")

    # Test 2: In-stock filtering (?in_stock=true)
    res = client.get('/api/user/products/search/?q=shirt&in_stock=true')
    assert res.status_code == 200
    data = res.json()
    assert data['total_matches'] == 1
    assert data['products'][0]['name'] == "Cotton Casual Denim Shirt"
    assert data['products'][0]['in_stock'] is True
    print("[PASS] Test 2: In-stock filter correctly excluded out-of-stock item")

    # Test 3: Price range filtering within test category (?category_id=...&min_price=1500)
    res = client.get(f'/api/user/products/search/?category_id={cat_a.id}&min_price=1500')
    assert res.status_code == 200
    data = res.json()
    assert data['total_matches'] == 1
    assert data['products'][0]['name'] == "Linen White Formal Shirt"
    print("[PASS] Test 3: Price range filtering (?min_price=1500) verified")

    # Test 4: Sorting by price_low_to_high within test category
    res = client.get(f'/api/user/products/search/?category_id={cat_a.id}&sort=price_low_to_high')
    assert res.status_code == 200
    data = res.json()
    prices = [p['discount_price'] or p['price'] for p in data['products']]
    assert prices == sorted(prices)
    print("[PASS] Test 4: Sorting by price_low_to_high verified")

    # Test 5: Category filter (?category_id=...)
    res = client.get(f'/api/user/products/search/?category_id={cat_b.id}')
    assert res.status_code == 200
    data = res.json()
    assert data['total_matches'] == 1
    assert data['products'][0]['name'] == "Leather Strap Classic Watch"
    print("[PASS] Test 5: Filter by category_id verified")

    # Test 6: Search multi-word query across vendor and description
    res = client.get('/api/user/products/search/?q=Apex denim')
    assert res.status_code == 200
    data = res.json()
    assert data['total_matches'] == 1
    assert data['products'][0]['name'] == "Cotton Casual Denim Shirt"
    print("[PASS] Test 6: Multi-word query across product and vendor verified")

    # Test 7: Error handling: min_price > max_price
    res = client.get('/api/user/products/search/?min_price=2000&max_price=1000')
    assert res.status_code == 400
    assert "cannot be greater than" in res.json()['message']
    print("[PASS] Test 7: Validation error on min_price > max_price returns 400")

    # Cleanup
    p1.delete()
    p2.delete()
    p3.delete()
    p4.delete()
    cat_a.delete()
    cat_b.delete()
    v1.delete()
    u1.delete()
    v2.delete()
    u2.delete()

    print("\n=======================================================")
    print(" ALL 7 PRODUCT SEARCH TESTS PASSED WITH 100% SUCCESS!")
    print("=======================================================\n")

if __name__ == '__main__':
    run_tests()
