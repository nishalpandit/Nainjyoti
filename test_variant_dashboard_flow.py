import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from nainjyoti.models import VendorProfile, Product, Category, ProductVariant, StockLog

def run_tests():
    print("=" * 60)
    print("TESTING DYNAMIC VARIANT MANAGEMENT APIS & DASHBOARDS")
    print("=" * 60)

    # 1. Setup Admin & Vendor fixtures
    admin_user, _ = User.objects.get_or_create(username="admin_test_var", defaults={"is_staff": True, "is_superuser": True})
    admin_user.set_password("AdminPass123!")
    admin_user.save()

    vendor_user, _ = User.objects.get_or_create(username="vendor_test_var", defaults={"is_staff": False})
    vendor_user.set_password("VendorPass123!")
    vendor_user.save()

    vendor, _ = VendorProfile.objects.get_or_create(
        user=vendor_user,
        defaults={
            "business_name": "Test Variant Store",
            "owner_name": "Test Owner",
            "phone": "9819999999",
            "status": "APPROVED",
            "auth_token": "test_vendor_token_12345"
        }
    )
    if not vendor.auth_token:
        vendor.auth_token = "test_vendor_token_12345"
        vendor.save()

    cat, _ = Category.objects.get_or_create(name="Test Apparel", defaults={"description": "Test Apparel Category", "status": "ACTIVE"})

    product, _ = Product.objects.get_or_create(
        vendor=vendor,
        name="Test Variant Polo Shirt",
        defaults={
            "category": cat,
            "sku": "POLO-001",
            "price": 1000.0,
            "discount_price": 850.0,
            "stock_quantity": 0,
            "status": "ACTIVE",
            "is_approved": True
        }
    )

    # Clean existing test variants
    product.variants.all().delete()
    product.sync_variant_inventory()

    client = Client()

    # 2. Test Admin Variant APIs
    client.force_login(admin_user)

    # Create variant via admin
    dummy_img = SimpleUploadedFile("var_red.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82", content_type="image/png")
    res = client.post(f"/api/admin/products/{product.id}/variants/create/", {
        "title": "Crimson Red / M",
        "color": "Red",
        "size": "M",
        "material": "Cotton",
        "price": 1200.0,
        "discount_price": 799.0,
        "stock_quantity": 15,
        "image": dummy_img,
        "is_active": "true"
    })
    assert res.status_code == 201 or res.status_code == 200, f"Admin variant create failed: {res.content}"
    data = res.json()
    assert data["success"] is True
    var1_id = data["variant"]["id"]
    print(f"[PASS] Admin created variant ID {var1_id}: '{data['variant']['title']}' (Effective: {data['variant']['effective_price']})")

    # Product stock should now equal 15
    product.refresh_from_db()
    assert product.has_variants is True
    assert product.variant_count == 1
    assert product.stock_quantity == 15
    assert product.customer_effective_price == 799.0
    print(f"[PASS] Product dynamic synchronization verified: stock={product.stock_quantity}, effective_price={product.customer_effective_price}")

    # List variants via admin
    res = client.get(f"/api/admin/products/{product.id}/variants/")
    assert res.status_code == 200
    data = res.json()
    assert len(data["variants"]) == 1
    print(f"[PASS] Admin listed variants: count={len(data['variants'])}")

    # 3. Test Vendor Variant APIs with Bearer token
    vendor_client = Client(HTTP_AUTHORIZATION=f"Bearer {vendor.auth_token}")
    
    # Create second variant via vendor API
    res = vendor_client.post(f"/api/vendor/products/{product.id}/variants/create/", {
        "title": "Ocean Blue / L",
        "color": "Blue",
        "size": "L",
        "material": "Pique Cotton",
        "price": 1250.0,
        "discount_price": 749.0,
        "stock_quantity": 25,
        "is_active": "true"
    })
    assert res.status_code == 201 or res.status_code == 200, f"Vendor variant create failed: {res.content}"
    data = res.json()
    assert data["success"] is True
    var2_id = data["variant"]["id"]
    print(f"[PASS] Vendor created variant ID {var2_id}: '{data['variant']['title']}' (Effective: {data['variant']['effective_price']})")

    product.refresh_from_db()
    assert product.variant_count == 2
    assert product.stock_quantity == 40  # 15 + 25
    assert product.customer_effective_price == 749.0  # min(799, 749)
    print(f"[PASS] Combined variant stock and minimum effective price verified: stock={product.stock_quantity}, price={product.customer_effective_price}")

    # Update variant via vendor API
    res = vendor_client.post(f"/api/vendor/variants/{var2_id}/update/", {
        "discount_price": 699.0,
        "stock_quantity": 30
    })
    assert res.status_code == 200, f"Vendor variant update failed: {res.content}"
    product.refresh_from_db()
    assert product.stock_quantity == 45  # 15 + 30
    assert product.customer_effective_price == 699.0
    print(f"[PASS] Vendor variant update updated parent product: stock={product.stock_quantity}, price={product.customer_effective_price}")

    # 4. Test Vendor Stock Adjustment with variant_id
    vendor_client.force_login(vendor_user)
    res = vendor_client.post(f"/vendor-dashboard/inventory/adjust/{product.id}/", {
        "variant_id": var1_id,
        "action": "RESTOCK",
        "quantity": 10,
        "reason": "Warehouse replenishment for Crimson Red / M"
    })
    assert res.status_code == 302, f"Vendor stock adjust failed: {res.content}"
    var1 = ProductVariant.objects.get(id=var1_id)
    assert var1.stock_quantity == 25, f"Expected 25, got {var1.stock_quantity}"
    product.refresh_from_db()
    assert product.stock_quantity == 55  # 25 + 30
    print(f"[PASS] Vendor stock adjustment on variant ID {var1_id} updated variant stock to 25 and parent to 55")

    # 5. Test Deactivate variant
    res = vendor_client.post(f"/api/vendor/variants/{var2_id}/update/", {
        "is_active": "false"
    })
    assert res.status_code == 200
    product.refresh_from_db()
    # Now only var1 is active (25 stock, price 799)
    assert product.stock_quantity == 25
    assert product.customer_effective_price == 799.0
    print(f"[PASS] Deactivating variant recalculated active stock to {product.stock_quantity} and price to {product.customer_effective_price}")

    # Reactivate var2
    vendor_client.post(f"/api/vendor/variants/{var2_id}/update/", {"is_active": "true"})

    # 6. Test Delete variant
    res = vendor_client.delete(f"/api/vendor/variants/{var2_id}/delete/")
    assert res.status_code == 200
    product.refresh_from_db()
    assert product.variant_count == 1
    assert product.stock_quantity == 25
    print(f"[PASS] Deleting variant ID {var2_id} updated variant count to 1 and stock to {product.stock_quantity}")

    # 7. Test Admin Products HTML rendering
    admin_client = Client()
    admin_client.force_login(admin_user)
    res = admin_client.get("/admin-dashboard/products/")
    assert res.status_code == 200
    html = res.content.decode("utf-8")
    assert "adminVariantsModal" in html
    assert "openAdminVariantsModal" in html
    print("[PASS] Admin products dashboard rendered with dynamic variant modal scripts")

    # 8. Test Vendor Products & Inventory HTML rendering
    res = vendor_client.get("/vendor-dashboard/products/")
    assert res.status_code == 200
    html = res.content.decode("utf-8")
    assert "vendorVariantsModal" in html
    assert "openVendorVariantsModal" in html
    print("[PASS] Vendor products dashboard rendered with dynamic variant modal scripts")

    res = vendor_client.get("/vendor-dashboard/inventory/")
    assert res.status_code == 200
    html = res.content.decode("utf-8")
    assert "Target Product Variant" in html
    print("[PASS] Vendor inventory dashboard rendered with target variant selector")

    res = vendor_client.get(f"/vendor-dashboard/products/{product.id}/edit/")
    assert res.status_code == 200
    html = res.content.decode("utf-8")
    assert "Locked: managed via variants" in html
    assert "readonly" in html
    print("[PASS] Vendor product form correctly locks stock input for products with variants")

    # Clean up test product
    product.variants.all().delete()
    product.delete()

    print("=" * 60)
    print("ALL 8 DYNAMIC VARIANT MANAGEMENT TEST SUITES PASSED (100%)")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
