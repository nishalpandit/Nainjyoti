import urllib.request
import urllib.parse
import json
import os
import io
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from nainjyoti.models import VendorProfile, Product

BASE_URL = "http://127.0.0.1:8000"

# A minimal valid 1x1 transparent PNG in bytes
SAMPLE_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00'
    b'\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)

def build_multipart(fields, files):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = io.BytesIO()

    for k, v in fields.items():
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        body.write(f"{v}\r\n".encode())

    for k, (filename, file_bytes, content_type) in files.items():
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="{k}"; filename="{filename}"\r\n'.encode())
        body.write(f'Content-Type: {content_type}\r\n\r\n'.encode())
        body.write(file_bytes)
        body.write(b"\r\n")

    body.write(f"--{boundary}--\r\n".encode())
    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': str(len(body.getvalue()))
    }
    return body.getvalue(), headers

def test_api_image_upload():
    print("\n[1] Testing REST API: POST /api/vendor/product/create/ with multipart image upload...")
    vendor = VendorProfile.objects.filter(user__username='merchant@crafts.in').first()
    assert vendor, "Vendor merchant@crafts.in not found!"

    fields = {
        'name': 'API Upload Test Handcrafted Copper Pot',
        'sku': f'COPPER-TEST-{os.urandom(3).hex().upper()}',
        'price': '2499.00',
        'stock_quantity': '15',
        'description': 'Handcrafted pure hammered copper pot with lid.'
    }
    files = {
        'image': ('copper_pot.png', SAMPLE_PNG_BYTES, 'image/png')
    }

    body, headers = build_multipart(fields, files)
    headers['Authorization'] = f'Bearer {vendor.auth_token}'

    req = urllib.request.Request(f"{BASE_URL}/api/vendor/product/create/", data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        status = resp.status
        data = json.loads(resp.read().decode('utf-8'))

    print(f" -> Status: {status}, Success: {data.get('success')}")
    assert status == 201
    assert data.get('success') is True
    prod = data.get('product', {})
    print(f" -> Created Product ID: {prod.get('id')}, Name: '{prod.get('name')}'")
    print(f" -> Uploaded Image URL: {prod.get('image')}")
    assert prod.get('image') is not None
    assert "/media/products/" in prod.get('image') or "/products/" in prod.get('image')
    print(" -> PASSED: Image file successfully uploaded and stored via API!")

    # Verify image is accessible via HTTP
    img_url = prod.get('image')
    if img_url.startswith('/'):
        img_url = f"{BASE_URL}{img_url}"
    req_img = urllib.request.Request(img_url)
    with urllib.request.urlopen(req_img) as resp_img:
        assert resp_img.status == 200
        print(f" -> Image file HTTP verification: Status {resp_img.status} (Content-Type: {resp_img.headers.get('Content-Type')})")

def test_web_image_upload():
    print("\n[2] Testing Web Dashboard: POST /vendor-dashboard/products/add/ with multipart image upload...")
    vendor = VendorProfile.objects.filter(user__username='merchant@crafts.in').first()

    fields = {
        'name': 'Web Dashboard Upload Test Pashmina Scarf',
        'sku': f'SCARF-TEST-{os.urandom(3).hex().upper()}',
        'price': '3199.00',
        'stock_quantity': '20',
        'description': 'Finely woven scarf uploaded via vendor dashboard form.',
        'status': 'ACTIVE'
    }
    files = {
        'image': ('scarf_photo.png', SAMPLE_PNG_BYTES, 'image/png')
    }

    from django.test import Client
    c = Client()
    c.force_login(vendor.user)

    upload_file = io.BytesIO(SAMPLE_PNG_BYTES)
    upload_file.name = 'scarf_photo.png'

    fields['image'] = upload_file
    response = c.post('/vendor-dashboard/products/add/', fields, follow=True)
    assert response.status_code == 200
    
    created_prod = Product.objects.filter(sku=fields['sku']).first()
    assert created_prod is not None
    print(f" -> Created Product via Web: ID {created_prod.id}, SKU: {created_prod.sku}")
    print(f" -> Saved Image Path: {created_prod.image}")
    print(f" -> Saved Image URL: {created_prod.image_url}")
    assert created_prod.image_url is not None
    assert "scarf_photo" in str(created_prod.image)
    print(" -> PASSED: Image file successfully uploaded and stored via Web Dashboard!")

if __name__ == '__main__':
    print("=" * 65)
    print(" TESTING IMAGE UPLOAD ON API AND WEB DASHBOARD ")
    print("=" * 65)
    test_api_image_upload()
    test_web_image_upload()
    print("\n" + "=" * 65)
    print(" BOTH API AND WEB DASHBOARD IMAGE UPLOADS VERIFIED 100%! ")
    print("=" * 65)
