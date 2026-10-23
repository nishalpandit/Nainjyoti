import os
import sys
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from nainjyoti.models import Category, Product, ProductVariant, VendorProfile

def run_tests():
    print("=" * 60)
    print("RUNNING STEP 7: PRODUCT DETAILS API TESTS")
    print("=" * 60)

    client = Client()

    # Clean up prior test data
    Category.objects.filter(name__in=["Details Test Cat Active", "Details Test Cat Inactive"]).delete()
    VendorProfile.objects.filter(vendor_code__in=["VEND-DTL1", "VEND-DTL2"]).delete()
    User.objects.filter(username__in=["usr_dtl_1", "usr_dtl_2"]).delete()

    cat_active = Category.objects.create(
        name="Details Test Cat Active",
        description="Active category for details test",
        status="ACTIVE"
    )
    cat_inactive = Category.objects.create(
        name="Details Test Cat Inactive",
        description="Deactivated category",
        status="INACTIVE"
    )

    # 1. Approved Vendor
    u1 = User.objects.create_user(username="usr_dtl_1")
    v1 = VendorProfile.objects.create(
        user=u1,
        vendor_code="VEND-DTL1",
        business_name="Apex Electronics Hub",
        owner_name="Siddharth Rao",
        phone="9876543201",
        city="Bengaluru",
        state="Karnataka",
        status="APPROVED"
    )

    # 2. Pending / Unapproved Vendor
    u2 = User.objects.create_user(username="usr_dtl_2")
    v2 = VendorProfile.objects.create(
        user=u2,
        vendor_code="VEND-DTL2",
        business_name="Unapproved Merchant",
        owner_name="Unapproved Owner",
        phone="9876543202",
        status="PENDING"
    )

    # 3. Primary Product with discount and variants
    p_primary = Product.objects.create(
        vendor=v1,
        category=cat_active,
        name="Wireless Noise Cancelling Headphones",
        sku="SKU-HEADPHONE-01",
        description="Premium over-ear wireless headphones with active noise cancellation and 30-hour battery life.",
        price=Decimal("2999.00"),
        discount_price=Decimal("2499.00"),
        stock_quantity=20,
        low_stock_threshold=5,
        unit="Piece",
        status="ACTIVE",
        is_approved=True
    )

    var1 = ProductVariant.objects.create(
        product=p_primary,
        title="Midnight Black",
        color="Black",
        size="Standard",
        material="Matte Plastic",
        sku="SKU-HEADPHONE-01-BLK",
        price=Decimal("2999.00"),
        discount_price=Decimal("2499.00"),
        stock_quantity=12,
        is_active=True
    )
    var2 = ProductVariant.objects.create(
        product=p_primary,
        title="Silver Edition",
        color="Silver",
        size="Standard",
        material="Brushed Aluminum",
        sku="SKU-HEADPHONE-01-SLV",
        price=Decimal("3299.00"),
        discount_price=Decimal("2699.00"),
        stock_quantity=8,
        is_active=True
    )

    # 4. Low stock product
    p_low_stock = Product.objects.create(
        vendor=v1,
        category=cat_active,
        name="Bluetooth True Wireless Earbuds",
        sku="SKU-EARBUD-01",
        description="Ergonomic IPX7 waterproof wireless earbuds",
        price=Decimal("1500.00"),
        discount_price=None,
        stock_quantity=3,
        low_stock_threshold=5,
        unit="Piece",
        status="ACTIVE",
        is_approved=True
    )

    # 5. Out of stock product
    p_out_of_stock = Product.objects.create(
        vendor=v1,
        category=cat_active,
        name="Studio Monitor Studio Speakers",
        sku="SKU-SPEAKER-01",
        description="High-fidelity balanced studio reference monitors",
        price=Decimal("8999.00"),
        discount_price=Decimal("7999.00"),
        stock_quantity=0,
        low_stock_threshold=5,
        unit="Pair",
        status="OUT_OF_STOCK",
        is_approved=True
    )

    # 6. Related product in same category
    p_related = Product.objects.create(
        vendor=v1,
        category=cat_active,
        name="Desktop USB DAC & Headphone Amp",
        sku="SKU-DAC-01",
        description="Compact audiophile DAC and amplifier",
        price=Decimal("4500.00"),
        discount_price=Decimal("3999.00"),
        stock_quantity=10,
        unit="Piece",
        status="ACTIVE",
        is_approved=True
    )

    # 7. Inactive product (status='INACTIVE')
    p_inactive = Product.objects.create(
        vendor=v1,
        category=cat_active,
        name="Discontinued Retro Cassette Player",
        sku="SKU-CASSETTE-01",
        description="Old stock discontinued product",
        price=Decimal("999.00"),
        stock_quantity=5,
        status="INACTIVE",
        is_approved=True
    )

    # 8. Unapproved product (is_approved=False)
    p_unapproved = Product.objects.create(
        vendor=v1,
        category=cat_active,
        name="Unverified Prototype Gadget",
        sku="SKU-PROTO-01",
        description="Prototype awaiting admin inspection",
        price=Decimal("1999.00"),
        stock_quantity=10,
        status="ACTIVE",
        is_approved=False
    )

    # 9. Product from unapproved vendor
    p_unapproved_vendor = Product.objects.create(
        vendor=v2,
        category=cat_active,
        name="Grey Market Portable Speaker",
        sku="SKU-GREY-01",
        description="From unverified seller",
        price=Decimal("499.00"),
        stock_quantity=10,
        status="ACTIVE",
        is_approved=True
    )

    # 10. Product under an inactive category
    p_inactive_cat = Product.objects.create(
        vendor=v1,
        category=cat_inactive,
        name="Hidden Deprecated Item",
        sku="SKU-HIDDEN-01",
        description="Product under deactivated category",
        price=Decimal("1200.00"),
        stock_quantity=10,
        status="ACTIVE",
        is_approved=True
    )

    print("[PASS] Fixtures initialized.")

    passed = 0
    total = 0

    # -------------------------------------------------------------
    # Test 1: Fetch primary product detail with discount & variants
    # -------------------------------------------------------------
    total += 1
    resp = client.get(f"/api/user/products/{p_primary.id}/")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.content}"
    data = resp.json()
    assert data["success"] is True
    prod = data["product"]
    assert prod["id"] == p_primary.id
    assert prod["name"] == "Wireless Noise Cancelling Headphones"
    assert prod["sku"] == "SKU-HEADPHONE-01"
    assert prod["price"] == 2999.0
    assert prod["discount_price"] == 2499.0
    assert prod["effective_price"] == 2499.0
    assert prod["savings_amount"] == 500.0
    assert prod["savings_percentage"] == 16.7
    assert prod["in_stock"] is True
    assert prod["low_stock_warning"] is False
    assert prod["category"]["id"] == cat_active.id
    assert prod["category"]["name"] == "Details Test Cat Active"
    assert prod["vendor"]["id"] == v1.id
    assert prod["vendor"]["business_name"] == "Apex Electronics Hub"
    assert prod["vendor"]["city"] == "Bengaluru"
    assert prod["has_variants"] is True
    assert prod["total_variants"] == 2
    assert "Black" in prod["available_colors"]
    assert "Silver" in prod["available_colors"]
    assert len(prod["variants"]) == 2
    # Verify related products list contains p_low_stock, p_out_of_stock, p_related, but NOT p_primary
    related_ids = [r["id"] for r in data["related_products"]]
    assert p_primary.id not in related_ids
    assert p_related.id in related_ids
    print("[PASS] Test 1: Full product detail, pricing, savings, vendor, category & variants.")
    passed += 1

    # -------------------------------------------------------------
    # Test 2: Low stock warning flag (stock_quantity <= low_stock_threshold)
    # -------------------------------------------------------------
    total += 1
    resp = client.get(f"/api/user/products/{p_low_stock.id}/")
    assert resp.status_code == 200
    data = resp.json()
    prod = data["product"]
    assert prod["in_stock"] is True
    assert prod["low_stock_warning"] is True
    assert prod["stock_quantity"] == 3
    assert prod["discount_price"] is None
    assert prod["effective_price"] == 1500.0
    assert prod["savings_amount"] == 0.0
    print("[PASS] Test 2: Low stock warning indicator.")
    passed += 1

    # -------------------------------------------------------------
    # Test 3: Out of stock product detail
    # -------------------------------------------------------------
    total += 1
    resp = client.get(f"/api/user/products/{p_out_of_stock.id}/")
    assert resp.status_code == 200
    data = resp.json()
    prod = data["product"]
    assert prod["in_stock"] is False
    assert prod["stock_quantity"] == 0
    assert prod["status"] == "OUT_OF_STOCK"
    print("[PASS] Test 3: Out-of-stock product details viewable with in_stock=false.")
    passed += 1

    # -------------------------------------------------------------
    # Test 4: Aliases: /api/user/product/detail/<id>/ and /api/products/<id>/
    # -------------------------------------------------------------
    total += 1
    resp_alias1 = client.get(f"/api/user/product/detail/{p_primary.id}/")
    resp_alias2 = client.get(f"/api/products/{p_primary.id}/")
    assert resp_alias1.status_code == 200
    assert resp_alias2.status_code == 200
    assert resp_alias1.json()["product"]["id"] == p_primary.id
    assert resp_alias2.json()["product"]["id"] == p_primary.id
    print("[PASS] Test 4: URL aliases work identically.")
    passed += 1

    # -------------------------------------------------------------
    # Test 5: Guardrail - 404 for non-existent product
    # -------------------------------------------------------------
    total += 1
    resp = client.get("/api/user/products/999999/")
    assert resp.status_code == 404
    data = resp.json()
    assert data["success"] is False
    assert "not found" in data["message"].lower()
    print("[PASS] Test 5: Non-existent product returns 404.")
    passed += 1

    # -------------------------------------------------------------
    # Test 6: Guardrail - 404 for INACTIVE product
    # -------------------------------------------------------------
    total += 1
    resp = client.get(f"/api/user/products/{p_inactive.id}/")
    assert resp.status_code == 404
    print("[PASS] Test 6: Inactive product returns 404.")
    passed += 1

    # -------------------------------------------------------------
    # Test 7: Guardrail - 404 for unapproved product
    # -------------------------------------------------------------
    total += 1
    resp = client.get(f"/api/user/products/{p_unapproved.id}/")
    assert resp.status_code == 404
    print("[PASS] Test 7: Unapproved product returns 404.")
    passed += 1

    # -------------------------------------------------------------
    # Test 8: Guardrail - 404 for product from unapproved vendor
    # -------------------------------------------------------------
    total += 1
    resp = client.get(f"/api/user/products/{p_unapproved_vendor.id}/")
    assert resp.status_code == 404
    print("[PASS] Test 8: Product from unapproved vendor returns 404.")
    passed += 1

    # -------------------------------------------------------------
    # Test 9: Guardrail - 404 for product under deactivated category
    # -------------------------------------------------------------
    total += 1
    resp = client.get(f"/api/user/products/{p_inactive_cat.id}/")
    assert resp.status_code == 404
    print("[PASS] Test 9: Product under inactive category returns 404.")
    passed += 1

    # -------------------------------------------------------------
    # Test 10: Method guardrail - POST returns 405
    # -------------------------------------------------------------
    total += 1
    resp = client.post(f"/api/user/products/{p_primary.id}/")
    assert resp.status_code == 405
    assert resp.json()["success"] is False
    print("[PASS] Test 10: POST request returns 405 Method Not Allowed.")
    passed += 1

    print("\n" + "=" * 60)
    print(f"ALL TESTS PASSED: {passed}/{total}")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
