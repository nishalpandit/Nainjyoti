import urllib.request
import urllib.parse
import urllib.error
import json
import uuid
import os
import django

# Setup Django environment to fetch test vendor credentials
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()
from django.contrib.auth.models import User
from nainjyoti.models import VendorProfile, Category, Product

BASE_URL = "http://127.0.0.1:8000"

TINY_PNG_BYTES = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
    0x00, 0x03, 0x01, 0x01, 0x00, 0x18, 0xDD, 0x8D,
    0xB0, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82
])

def encode_multipart_formdata(fields, files):
    boundary = f"----FormBoundary{uuid.uuid4().hex}"
    CRLF = b"\r\n"
    lines = []
    
    for key, val in fields.items():
        if val is not None:
            lines.append(f"--{boundary}".encode("utf-8"))
            lines.append(f'Content-Disposition: form-data; name="{key}"'.encode("utf-8"))
            lines.append(b"")
            lines.append(str(val).encode("utf-8"))
            
    for key, (filename, file_bytes, content_type) in files.items():
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode("utf-8"))
        lines.append(f'Content-Type: {content_type}'.encode("utf-8"))
        lines.append(b"")
        lines.append(file_bytes)
        
    lines.append(f"--{boundary}--".encode("utf-8"))
    lines.append(b"")
    body = CRLF.join(lines)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))
    }
    return body, headers

def send_request(method, path, data=None, headers=None):
    url = f"{BASE_URL}{path}"
    headers = headers or {}
    body = None

    if data is not None:
        if isinstance(data, (bytes, bytearray)):
            body = data
        elif isinstance(data, dict):
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            if headers.get("Content-Type") == "application/json":
                body = json.dumps(data).encode("utf-8")
            else:
                body = urllib.parse.urlencode(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            res_body = resp.read().decode("utf-8")
            try:
                return status, json.loads(res_body)
            except Exception:
                return status, res_body
    except urllib.error.HTTPError as e:
        status = e.code
        res_body = e.read().decode("utf-8")
        try:
            return status, json.loads(res_body)
        except Exception:
            return status, res_body

def setup_vendors():
    # Vendor A
    u_a, _ = User.objects.get_or_create(username='vendor_a@nainjyoti.com', defaults={'email': 'vendor_a@nainjyoti.com'})
    v_a, _ = VendorProfile.objects.get_or_create(user=u_a, defaults={
        'business_name': 'Kashmir Pashmina & Crafts',
        'owner_name': 'Tariq Butt',
        'phone': '9876543210',
        'status': 'APPROVED'
    })
    v_a.status = 'APPROVED'
    if not v_a.auth_token:
        v_a.generate_new_token()
    v_a.save()

    # Vendor B
    u_b, _ = User.objects.get_or_create(username='vendor_b@nainjyoti.com', defaults={'email': 'vendor_b@nainjyoti.com'})
    v_b, _ = VendorProfile.objects.get_or_create(user=u_b, defaults={
        'business_name': 'Jaipur Blue Pottery Store',
        'owner_name': 'Rajesh Sharma',
        'phone': '9876543299',
        'status': 'APPROVED'
    })
    v_b.status = 'APPROVED'
    if not v_b.auth_token:
        v_b.generate_new_token()
    v_b.save()

    return v_a, v_b

def run_tests():
    results = {}
    print("=" * 65)
    print(" STARTING SECURED PRODUCT MANAGEMENT API TEST SUITE ")
    print("=" * 65)

    vendor_a, vendor_b = setup_vendors()
    token_a = vendor_a.auth_token
    token_b = vendor_b.auth_token
    print(f" -> Authenticated Vendor A: {vendor_a.business_name} (ID: {vendor_a.id})")
    print(f" -> Authenticated Vendor B: {vendor_b.business_name} (ID: {vendor_b.id})")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Test 401 Unauthorized when Bearer token is missing
    print("\n[1] Testing Security: Missing Bearer Token on /api/vendor/product/list/...")
    st_no_auth, resp_no_auth = send_request("GET", "/api/vendor/product/list/")
    print(f" -> Status: {st_no_auth}")
    print(f" -> Response: {resp_no_auth}")
    assert st_no_auth == 401, f"Expected 401, got {st_no_auth}"
    assert resp_no_auth.get("success") is False
    print(" -> PASSED: Strict 401 Unauthorized enforced when token is missing!")

    # 2. Test 401 Unauthorized when Bearer token is invalid
    print("\n[2] Testing Security: Invalid Bearer Token on /api/vendor/product/list/...")
    st_bad_auth, resp_bad_auth = send_request("GET", "/api/vendor/product/list/", headers={"Authorization": "Bearer invalid_secret_token_12345"})
    print(f" -> Status: {st_bad_auth}")
    assert st_bad_auth == 401
    print(" -> PASSED: Strict 401 Unauthorized enforced for invalid token!")

    # 3. Ensure a master Category exists
    print("\n[3] Ensuring Master Category exists...")
    cat_payload = {"name": "Electronics & Wearables", "status": "ACTIVE"}
    st, resp = send_request("POST", "/api/vendor/category/create/", data=cat_payload)
    if st == 201:
        category_id = resp["category"]["id"]
        category_name = resp["category"]["name"]
        print(f" -> Created new category: {category_name} (ID: {category_id})")
    else:
        st_list, resp_list = send_request("GET", "/api/vendor/category/list/")
        cats = resp_list.get("categories", [])
        if cats:
            category_id = cats[0]["id"]
            category_name = cats[0]["name"]
            print(f" -> Using existing category: {category_name} (ID: {category_id})")
        else:
            raise Exception("No categories found.")

    # 4. Test Product Creation with Vendor A Bearer token (Multipart form with Image)
    print("\n[4] Testing POST /api/vendor/product/create/ (Vendor A with Multipart Image)...")
    sku_unique = f"WATCH-{uuid.uuid4().hex[:6].upper()}"
    fields = {
        'name': 'Wireless Noise Cancelling Smart Watch Pro',
        'sku': sku_unique,
        'category_id': category_id,
        'price': '3499.00',
        'discount_price': '2999.00',
        'stock_quantity': '50',
        'unit': 'Piece',
        'description': 'High-performance smartwatch featuring OLED display, health tracking, and 7-day battery life.',
        'status': 'ACTIVE'
    }
    files = {
        'image': ('smart_watch.png', TINY_PNG_BYTES, 'image/png')
    }
    body, mp_headers = encode_multipart_formdata(fields, files)
    mp_headers.update(headers_a)

    st_create, resp_create = send_request("POST", "/api/vendor/product/create/", data=body, headers=mp_headers)
    print(f" -> Status Code: {st_create}")
    print(f" -> Response: {json.dumps(resp_create, indent=2)}")
    assert st_create == 201, f"Expected 201, got {st_create}"
    product_id = resp_create["product"]["id"]
    created_prod = resp_create["product"]
    assert created_prod["name"] == fields["name"]
    assert created_prod["vendor_id"] == vendor_a.id, "Product must be owned strictly by Vendor A!"
    print(f" -> Success! Created Product ID {product_id} bound to Vendor {created_prod['vendor_id']}")

    # 5. Test Product Detail with Vendor A
    print(f"\n[5] Testing GET /api/vendor/product/detail/{product_id}/ with Vendor A...")
    st_det, resp_det = send_request("GET", f"/api/vendor/product/detail/{product_id}/", headers=headers_a)
    print(f" -> Status Code: {st_det}")
    assert st_det == 200
    assert resp_det["product"]["id"] == product_id

    # 6. Test Multi-tenant Security: Vendor B attempts to view Vendor A's product -> 403 Forbidden!
    print(f"\n[6] Testing Security: Vendor B attempts to view Vendor A's product detail (ID {product_id})...")
    st_cross_view, resp_cross_view = send_request("GET", f"/api/vendor/product/detail/{product_id}/", headers=headers_b)
    print(f" -> Status: {st_cross_view}")
    print(f" -> Response: {resp_cross_view}")
    assert st_cross_view == 403, f"Expected 403 Forbidden, got {st_cross_view}"
    assert "Access denied" in resp_cross_view.get("message", "")
    print(" -> PASSED: Multi-tenant boundary enforced! Vendor B cannot view Vendor A's product.")

    # 7. Test Multi-tenant Security: Vendor B attempts to update Vendor A's product -> 403 Forbidden!
    print(f"\n[7] Testing Security: Vendor B attempts to update Vendor A's product (ID {product_id})...")
    st_cross_upd, resp_cross_upd = send_request("POST", f"/api/vendor/product/update/{product_id}/", data={"price": "100.00"}, headers=headers_b)
    print(f" -> Status: {st_cross_upd}")
    assert st_cross_upd == 403
    assert "Access denied" in resp_cross_upd.get("message", "")
    print(" -> PASSED: Vendor B forbidden from modifying Vendor A's product!")

    # 8. Test Product Update with Vendor A (Rightful owner)
    print(f"\n[8] Testing POST /api/vendor/product/update/{product_id}/ by Vendor A...")
    update_data = {
        'price': '3199.00',
        'discount_price': '2799.00',
        'stock_quantity': '42',
        'description': 'Updated: Now includes 2 additional magnetic bands and 10-day battery.',
        'status': 'ACTIVE'
    }
    st_upd, resp_upd = send_request("POST", f"/api/vendor/product/update/{product_id}/", data=update_data, headers=headers_a)
    print(f" -> Status Code: {st_upd}")
    assert st_upd == 200
    assert resp_upd["product"]["price"] == 3199.0
    assert resp_upd["product"]["stock_quantity"] == 42
    print(" -> Product updated successfully by rightful owner.")

    # 9. Create Product #2 for Vendor A
    print("\n[9] Creating Product #2 for Vendor A (Out of stock item)...")
    sku2_unique = f"KEY-{uuid.uuid4().hex[:6].upper()}"
    prod2_payload = {
        'name': 'Ergonomic Wireless Mechanical Keyboard',
        'sku': sku2_unique,
        'category_id': category_id,
        'price': '1599.00',
        'discount_price': '1399.00',
        'stock_quantity': '0',
        'unit': 'Piece',
        'description': 'RGB backlit wireless keyboard with brown switches.',
        'status': 'OUT_OF_STOCK'
    }
    st_p2, resp_p2 = send_request("POST", "/api/vendor/product/create/", data=prod2_payload, headers=headers_a)
    assert st_p2 == 201
    prod2_id = resp_p2["product"]["id"]

    # 10. Test Multi-tenant Product List Scoping
    print("\n[10] Testing GET /api/vendor/product/list/ multi-tenant scoping...")
    st_list_a, resp_list_a = send_request("GET", "/api/vendor/product/list/", headers=headers_a)
    assert st_list_a == 200
    a_ids = [p["id"] for p in resp_list_a.get("products", [])]
    assert product_id in a_ids and prod2_id in a_ids
    print(f" -> Vendor A sees {len(a_ids)} items (both owned items present)")

    st_list_b, resp_list_b = send_request("GET", "/api/vendor/product/list/", headers=headers_b)
    assert st_list_b == 200
    b_ids = [p["id"] for p in resp_list_b.get("products", [])]
    assert product_id not in b_ids and prod2_id not in b_ids, "Vendor A's products leaked to Vendor B!"
    print(f" -> Vendor B sees {len(b_ids)} items (ZERO of Vendor A's items leaked!)")

    # 11. Test Multi-tenant Security: Vendor B attempts to delete Vendor A's product -> 403 Forbidden!
    print(f"\n[11] Testing Security: Vendor B attempts to delete Vendor A's product (ID {prod2_id})...")
    st_cross_del, resp_cross_del = send_request("POST", f"/api/vendor/product/delete/{prod2_id}/", headers=headers_b)
    print(f" -> Status: {st_cross_del}")
    assert st_cross_del == 403
    print(" -> PASSED: Vendor B forbidden from deleting Vendor A's product!")

    # 12. Rightful Delete of Product #2 by Vendor A
    print(f"\n[12] Testing Rightful DELETE by Vendor A on Product {prod2_id}...")
    st_del, resp_del = send_request("POST", f"/api/vendor/product/delete/{prod2_id}/", headers=headers_a)
    assert st_del == 200
    assert resp_del["success"] is True

    st_chk, _ = send_request("GET", f"/api/vendor/product/detail/{prod2_id}/", headers=headers_a)
    assert st_chk == 404
    print(" -> Product 2 successfully deleted and confirmed 404.")

    # 13. Test Public / Admin Aliases
    print("\n[13] Testing Public / Admin Product Aliases...")
    st_pub, resp_pub = send_request("GET", "/api/product/list/")
    assert st_pub == 200
    st_adm, resp_adm = send_request("GET", f"/api/admin/product/detail/{product_id}/")
    assert st_adm == 200
    print(" -> Public and Admin aliases operating normally.")

    # Save test results
    results["vendor_a_id"] = vendor_a.id
    results["vendor_b_id"] = vendor_b.id
    results["test_product_id"] = product_id
    results["security_tests_passed"] = ["401_missing_token", "401_invalid_token", "403_cross_view", "403_cross_update", "403_cross_delete", "tenant_isolation_list"]
    with open("product_api_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 65)
    print(" ALL PRODUCT API SECURITY & FUNCTIONAL TESTS PASSED 100%! ")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
