import os
import django
import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client
from nainjyoti.models import Product, VendorProfile, Category

vendor = VendorProfile.objects.filter(auth_token="589031eb3c3b5a16bd354e88aa884e9611a827b9145f08c3d1beb090c8674584").first()
if not vendor:
    vendor = VendorProfile.objects.filter(status="APPROVED").first()
token = vendor.auth_token

category = Category.objects.first()
category_id = category.id if category else 1

print("==========================================================")
print(" LIVE TEST: PRODUCT CREATE WITH MULTIPART/FORM-DATA")
print("==========================================================")
print(f"Vendor: {vendor.business_name} (ID: {vendor.id})")
print(f"Token: {token[:12]}...")
print(f"Target Category ID: {category_id} ({category.name if category else 'Default'})")

# 1. Create a genuine test image in memory
img_buffer = io.BytesIO()
img = Image.new('RGB', (100, 100), color=(50, 120, 80))
img.save(img_buffer, format='PNG')
img_bytes = img_buffer.getvalue()

uploaded_image = SimpleUploadedFile("smart_watch_test.png", img_bytes, content_type="image/png")

# 2. Prepare multipart form data payload
test_sku = "WATCH-TEST-999"
Product.objects.filter(sku=test_sku).delete()

payload_data = {
    "name": "Wireless Noise Cancelling Smart Watch Pro Test",
    "sku": test_sku,
    "category_id": str(category_id),
    "price": "3499.00",
    "discount_price": "2999.00",
    "stock_quantity": "50",
    "low_stock_threshold": "10",
    "unit": "Piece",
    "description": "High-performance smartwatch featuring OLED display, health tracking, and 7-day battery life.",
    "status": "ACTIVE",
    "image": uploaded_image
}

client = Client()
headers = {
    "HTTP_AUTHORIZATION": f"Bearer {token}"
}

url = "/api/vendor/product/create/"

print(f"\nSending POST multipart/form-data request to: {url}")
response = client.post(url, data=payload_data, **headers)

print(f"HTTP Status: {response.status_code}")
resp_json = response.json()
print("API Response JSON:")
import pprint
pprint.pprint(resp_json)

assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
assert resp_json.get("success") is True, "Expected success to be True"

created_product_id = resp_json["product"]["id"]
print(f"\n [PASS] Product created successfully with ID: {created_product_id}")

# 3. VERIFY IN DATABASE
print("\nVerifying database state...")
db_product = Product.objects.filter(id=created_product_id).first()
assert db_product is not None, f"Product ID {created_product_id} not found in database!"
assert db_product.name == payload_data["name"]
assert float(db_product.price) == 3499.0
assert float(db_product.discount_price) == 2999.0
assert db_product.stock_quantity == 50
assert db_product.sku == test_sku
assert db_product.vendor_id == vendor.id
assert db_product.image is not None and len(str(db_product.image)) > 0

print(f" [DATABASE VERIFIED]")
print(f" - Product ID in DB: {db_product.id}")
print(f" - Name in DB: {db_product.name}")
print(f" - Price in DB: INR {db_product.price}")
print(f" - Stock in DB: {db_product.stock_quantity}")
print(f" - Vendor in DB: {db_product.vendor.business_name} (ID: {db_product.vendor_id})")
print(f" - Category in DB: {db_product.category.name if db_product.category else 'None'} (ID: {db_product.category_id})")
print(f" - Image Path in DB: {db_product.image.name}")
print(f" - Image URL via property: {db_product.image_url}")

# Verify file actually exists on filesystem
image_file_path = db_product.image.path
print(f" - Physical file path: {image_file_path}")
assert os.path.exists(image_file_path), f"File {image_file_path} does not exist on disk!"
print(f" - Physical file size: {os.path.getsize(image_file_path)} bytes")

# 4. TEST MULTIPART UPDATE TO MAKE SURE UPDATE ALSO WORKS
print("\nTesting Update Product via multipart/form-data...")
update_url = f"/api/vendor/product/update/{created_product_id}/"

img_buffer_update = io.BytesIO()
img_update = Image.new('RGB', (120, 120), color=(180, 50, 50))
img_update.save(img_buffer_update, format='PNG')
uploaded_update_image = SimpleUploadedFile("updated_watch.png", img_buffer_update.getvalue(), content_type="image/png")

update_data = {
    "price": "3199.00",
    "discount_price": "2799.00",
    "stock_quantity": "42",
    "description": "Updated: Now includes 2 additional magnetic bands and 10-day battery.",
    "image": uploaded_update_image
}

resp_update = client.post(update_url, data=update_data, **headers)
print(f"Update HTTP Status: {resp_update.status_code}")
resp_update_json = resp_update.json()
assert resp_update.status_code == 200
assert resp_update_json["success"] is True

# Verify DB after update
db_product.refresh_from_db()
assert float(db_product.price) == 3199.0
assert float(db_product.discount_price) == 2799.0
assert db_product.stock_quantity == 42
assert "Updated:" in db_product.description
assert os.path.exists(db_product.image.path)

print(f" [PASS] Update verified in database: New Price INR {db_product.price}, New Stock {db_product.stock_quantity}, Image: {db_product.image.name}")

print("\n==========================================================")
print(" ALL MULTIPART/FORM-DATA AND DATABASE TESTS PASSED 100%!")
print("==========================================================")
