import os
import sys
import django
import io
from decimal import Decimal
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from nainjyoti.models import Category, Product, VendorProfile

def create_test_image(name="cat_icon.png", color="orange"):
    file_obj = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=color)
    img.save(file_obj, format="PNG")
    file_obj.seek(0)
    return SimpleUploadedFile(name, file_obj.read(), content_type="image/png")

def run_tests():
    print("=" * 60)
    print("RUNNING STEP 5: PRODUCT CATEGORIES & ADMIN CONTROL TESTS")
    print("=" * 60)

    client = Client()

    # 1. Setup Test Data
    # Cleanup previous test records
    Category.objects.filter(name__in=["Test Active Category", "Test Inactive Category"]).delete()
    VendorProfile.objects.filter(vendor_code="VEND-TESTCAT").delete()
    User.objects.filter(username="usr_test_cat_vendor").delete()

    cat_active = Category.objects.create(
        name="Test Active Category",
        description="Premium items for testing",
        status="ACTIVE"
    )
    cat_inactive = Category.objects.create(
        name="Test Inactive Category",
        description="Hidden category",
        status="INACTIVE"
    )

    vendor_user = User.objects.create_user(username="usr_test_cat_vendor")
    vendor = VendorProfile.objects.create(
        user=vendor_user,
        vendor_code="VEND-TESTCAT",
        business_name="Test Category Store",
        owner_name="Test Owner",
        phone="9988776655",
        status="APPROVED"
    )

    # Create products under active category
    p1 = Product.objects.create(
        vendor=vendor,
        category=cat_active,
        name="Product Alpha",
        sku="SKU-CAT-01",
        price=Decimal("1500.00"),
        discount_price=Decimal("1200.00"),
        stock_quantity=20,
        status="ACTIVE",
        is_approved=True
    )
    p2 = Product.objects.create(
        vendor=vendor,
        category=cat_active,
        name="Product Beta",
        sku="SKU-CAT-02",
        price=Decimal("800.00"),
        discount_price=None,
        stock_quantity=10,
        status="ACTIVE",
        is_approved=True
    )
    # Inactive product (should not appear in customer category products)
    p_inactive = Product.objects.create(
        vendor=vendor,
        category=cat_active,
        name="Product Hidden",
        sku="SKU-CAT-03",
        price=Decimal("500.00"),
        stock_quantity=5,
        status="INACTIVE",
        is_approved=True
    )

    print("[PASS] Test fixtures created successfully")

    # Test 1: GET /api/user/categories/ (Only active categories returned)
    res = client.get('/api/user/categories/')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data['success'] is True
    names = [c['name'] for c in data['categories']]
    assert "Test Active Category" in names
    assert "Test Inactive Category" not in names
    active_cat_item = next(c for c in data['categories'] if c['name'] == "Test Active Category")
    assert active_cat_item['products_count'] == 2  # Only 2 active approved products
    print(f"[PASS] Test 1: GET /api/user/categories/ returns active categories with live products_count ({active_cat_item['products_count']})")

    # Test 2: Search within categories (?q=...)
    res = client.get('/api/user/categories/?q=Active')
    assert res.status_code == 200
    data = res.json()
    assert data['count'] >= 1
    assert any("Active" in c['name'] for c in data['categories'])
    print("[PASS] Test 2: Category search filter (?q=...) works as expected")

    # Test 3: GET /api/user/categories/<id>/ (Category Detail)
    res = client.get(f'/api/user/categories/{cat_active.id}/')
    assert res.status_code == 200
    data = res.json()
    assert data['success'] is True
    assert data['category']['id'] == cat_active.id
    assert data['category']['name'] == "Test Active Category"
    print(f"[PASS] Test 3: GET /api/user/categories/{cat_active.id}/ returns category detail")

    # Test 4: GET /api/user/categories/<id>/ on Inactive Category returns 404
    res = client.get(f'/api/user/categories/{cat_inactive.id}/')
    assert res.status_code == 404
    print("[PASS] Test 4: Inactive category detail returns 404 to customer")

    # Test 5: GET /api/user/categories/<id>/products/ (Products under category with sorting)
    res = client.get(f'/api/user/categories/{cat_active.id}/products/?sort=price_low_to_high')
    assert res.status_code == 200
    data = res.json()
    assert data['success'] is True
    assert data['total_products'] == 2
    prods = data['products']
    assert len(prods) == 2
    # Product Beta has price 800, Product Alpha has effective price 1200
    assert prods[0]['name'] == "Product Beta"
    assert prods[1]['name'] == "Product Alpha"
    print("[PASS] Test 5: Category products fetched and correctly sorted by price_low_to_high")

    # Test 6: Price filtering inside category products
    res = client.get(f'/api/user/categories/{cat_active.id}/products/?min_price=1000')
    assert res.status_code == 200
    data = res.json()
    assert data['total_products'] == 1
    assert data['products'][0]['name'] == "Product Alpha"
    print("[PASS] Test 6: Category products price filtering (?min_price=1000) verified")

    # Test 7: Admin Control: Toggle Category to INACTIVE
    res = client.post(f'/admin-dashboard/categories/{cat_active.id}/toggle-status/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert res.status_code == 200
    data = res.json()
    assert data['success'] is True
    assert data['status'] == 'INACTIVE'
    cat_active.refresh_from_db()
    assert cat_active.status == 'INACTIVE'
    print("[PASS] Test 7: Admin toggled category status to INACTIVE")

    # Test 8: Inactive Category is now immediately hidden from API
    res = client.get(f'/api/user/categories/{cat_active.id}/products/')
    assert res.status_code == 404
    res_list = client.get('/api/user/categories/')
    assert "Test Active Category" not in [c['name'] for c in res_list.json()['categories']]
    print("[PASS] Test 8: Deactivated category is immediately hidden from customer APIs (returns 404)")

    # Test 9: Admin Control: Toggle Category back to ACTIVE
    res = client.post(f'/admin-dashboard/categories/{cat_active.id}/toggle-status/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert res.status_code == 200
    cat_active.refresh_from_db()
    assert cat_active.status == 'ACTIVE'
    res = client.get(f'/api/user/categories/{cat_active.id}/products/')
    assert res.status_code == 200
    print("[PASS] Test 9: Admin activated category, products immediately available again")

    # Test 10: Admin Form Edit with Image Upload & Description
    cat_img = create_test_image("test_cat.png", "purple")
    res = client.post(f'/admin-dashboard/categories/{cat_active.id}/edit/', {
        'name': 'Test Active Category Renamed',
        'description': 'Updated description via admin',
        'status': 'ACTIVE',
        'image': cat_img
    })
    assert res.status_code in [200, 302]
    cat_active.refresh_from_db()
    assert cat_active.name == 'Test Active Category Renamed'
    assert cat_active.description == 'Updated description via admin'
    assert cat_active.image_url is not None
    print(f"[PASS] Test 10: Admin edit category with image upload verified: {cat_active.image_url}")

    # Cleanup
    cat_active.delete()
    cat_inactive.delete()
    p1.delete()
    p2.delete()
    p_inactive.delete()
    vendor.delete()
    vendor_user.delete()

    print("\n=======================================================")
    print(" ALL 10 CATEGORY TESTS PASSED WITH 100% SUCCESS!")
    print("=======================================================\n")

if __name__ == '__main__':
    run_tests()
