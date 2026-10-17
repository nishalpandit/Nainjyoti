import urllib.request
import urllib.parse
import urllib.error
import json
import uuid
import os

BASE_URL = "http://127.0.0.1:8000"

# Minimal valid 1x1 PNG byte array for realistic image upload testing
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

def run_tests():
    results = {}
    print("=" * 65)
    print(" STARTING PRODUCT MANAGEMENT API TEST SUITE ")
    print("=" * 65)

    # 1. Ensure a master Category exists
    print("\n[1] Ensuring Master Category exists...")
    cat_payload = {"name": "Electronics & Gadgets", "status": "ACTIVE"}
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

    # 2. Test Product Creation with Multipart Form-Data and Image Upload
    print("\n[2] Testing POST /api/vendor/product/create/ (Multipart Form-Data with Image)...")
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
    body, headers = encode_multipart_formdata(fields, files)

    st_create, resp_create = send_request("POST", "/api/vendor/product/create/", data=body, headers=headers)
    print(f" -> Status Code: {st_create}")
    print(f" -> Response: {json.dumps(resp_create, indent=2)}")
    results["1_product_create_multipart"] = {
        "status_code": st_create,
        "response": resp_create
    }
    assert st_create == 201, f"Expected 201, got {st_create}"
    product_id = resp_create["product"]["id"]
    created_prod = resp_create["product"]
    assert created_prod["name"] == fields["name"]
    assert created_prod["sku"] == fields["sku"]
    assert created_prod["price"] == 3499.0
    assert created_prod["discount_price"] == 2999.0
    assert created_prod["image"] is not None and "products/" in created_prod["image"], "Image URL was not saved!"
    print(f" -> Success! Created Product ID {product_id} with Image: {created_prod['image']}")

    # 3. Test Product Detail API
    print(f"\n[3] Testing GET /api/vendor/product/detail/{product_id}/...")
    st_det, resp_det = send_request("GET", f"/api/vendor/product/detail/{product_id}/")
    print(f" -> Status Code: {st_det}")
    print(f" -> Response: {json.dumps(resp_det, indent=2)}")
    results["2_product_detail"] = {
        "status_code": st_det,
        "response": resp_det
    }
    assert st_det == 200
    assert resp_det["product"]["id"] == product_id
    assert resp_det["product"]["category_name"] == category_name

    # 4. Test Product Update API
    print(f"\n[4] Testing POST /api/vendor/product/update/{product_id}/...")
    update_data = {
        'price': '3199.00',
        'discount_price': '2799.00',
        'stock_quantity': '42',
        'description': 'Updated: Now includes 2 additional magnetic bands and 10-day battery.',
        'status': 'ACTIVE'
    }
    st_upd, resp_upd = send_request("POST", f"/api/vendor/product/update/{product_id}/", data=update_data)
    print(f" -> Status Code: {st_upd}")
    print(f" -> Response: {json.dumps(resp_upd, indent=2)}")
    results["3_product_update"] = {
        "status_code": st_upd,
        "response": resp_upd
    }
    assert st_upd == 200
    assert resp_upd["product"]["price"] == 3199.0
    assert resp_upd["product"]["stock_quantity"] == 42

    # 5. Create a second product to test filters and search
    print("\n[5] Testing POST /api/vendor/product/create/ (Product #2: Out of Stock item)...")
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
    st_p2, resp_p2 = send_request("POST", "/api/vendor/product/create/", data=prod2_payload)
    print(f" -> Status Code: {st_p2}")
    print(f" -> Response: {json.dumps(resp_p2, indent=2)}")
    assert st_p2 == 201
    prod2_id = resp_p2["product"]["id"]
    results["4_product_create_second"] = {
        "status_code": st_p2,
        "response": resp_p2
    }

    # 6. Test Product Listing with Filters
    print("\n[6] Testing GET /api/vendor/product/list/ with query filters...")

    # 6a. All products
    st_list, resp_list = send_request("GET", "/api/vendor/product/list/")
    print(f" -> [All Products] Count: {resp_list.get('count')}")
    assert st_list == 200 and resp_list.get('count') >= 2
    results["5a_product_list_all"] = {
        "status_code": st_list,
        "count": resp_list.get("count"),
        "products": resp_list.get("products")
    }

    # 6b. Search filter
    st_srch, resp_srch = send_request("GET", "/api/vendor/product/list/?search=Mechanical")
    print(f" -> [Search 'Mechanical'] Count: {resp_srch.get('count')}")
    assert st_srch == 200 and resp_srch.get('count') >= 1
    results["5b_product_list_search"] = {
        "status_code": st_srch,
        "count": resp_srch.get("count")
    }

    # 6c. Status filter
    st_st, resp_st = send_request("GET", "/api/vendor/product/list/?status=OUT_OF_STOCK")
    print(f" -> [Status 'OUT_OF_STOCK'] Count: {resp_st.get('count')}")
    assert st_st == 200 and resp_st.get('count') >= 1
    results["5c_product_list_status"] = {
        "status_code": st_st,
        "count": resp_st.get("count")
    }

    # 6d. Price range filter
    st_pr, resp_pr = send_request("GET", "/api/vendor/product/list/?min_price=2000&max_price=4000")
    print(f" -> [Price Range INR 2000 - INR 4000] Count: {resp_pr.get('count')}")
    assert st_pr == 200 and resp_pr.get('count') >= 1
    results["5d_product_list_price_range"] = {
        "status_code": st_pr,
        "count": resp_pr.get("count")
    }

    # 7. Test Delete Product API
    print(f"\n[7] Testing POST /api/vendor/product/delete/{prod2_id}/...")
    st_del, resp_del = send_request("POST", f"/api/vendor/product/delete/{prod2_id}/")
    print(f" -> Status Code: {st_del}")
    print(f" -> Response: {json.dumps(resp_del, indent=2)}")
    results["6_product_delete"] = {
        "status_code": st_del,
        "response": resp_del
    }
    assert st_del == 200
    assert resp_del["success"] is True

    # 8. Verify deleted product returns 404
    print(f"\n[8] Verifying deleted product is 404...")
    st_chk, resp_chk = send_request("GET", f"/api/vendor/product/detail/{prod2_id}/")
    print(f" -> Status Code: {st_chk} (Expected 404)")
    assert st_chk == 404
    results["7_product_verify_404"] = {
        "status_code": st_chk,
        "response": resp_chk
    }

    # 9. Test Aliases: GET /api/product/list/ and GET /api/admin/product/detail/<id>/
    print(f"\n[9] Testing API aliases (/api/product/list/ and /api/admin/product/detail/{product_id}/)...")
    st_alias1, resp_alias1 = send_request("GET", "/api/product/list/")
    assert st_alias1 == 200
    st_alias2, resp_alias2 = send_request("GET", f"/api/admin/product/detail/{product_id}/")
    assert st_alias2 == 200
    print(f" -> Aliases work identically! Product name: {resp_alias2['product']['name']}")

    # Save complete test suite results to JSON file
    with open("product_api_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 65)
    print(" ALL PRODUCT API SUITE TESTS PASSED 100% SUCCESSFULLY! ")
    print(" Full logs written to: product_api_test_results.json")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
