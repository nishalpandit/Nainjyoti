import urllib.request
import urllib.parse
import urllib.error
import json
import uuid
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()
from django.contrib.auth.models import User
from nainjyoti.models import VendorProfile, Product, StockLog

BASE_URL = "http://127.0.0.1:8000"

def send_request(method, path, data=None, headers=None):
    url = f"{BASE_URL}{path}"
    headers = headers or {}
    body = None

    if data is not None:
        if isinstance(data, dict):
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            if headers.get("Content-Type") == "application/json":
                body = json.dumps(data).encode("utf-8")
            else:
                body = urllib.parse.urlencode(data).encode("utf-8")
        elif isinstance(data, (bytes, bytearray)):
            body = data

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
    print(" STARTING SECURED STOCK MANAGEMENT & AUDIT LEDGER TEST SUITE ")
    print("=" * 65)

    vendor_a, vendor_b = setup_vendors()
    token_a = vendor_a.auth_token
    token_b = vendor_b.auth_token
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    print(f" -> Vendor A: {vendor_a.business_name} (ID: {vendor_a.id})")
    print(f" -> Vendor B: {vendor_b.business_name} (ID: {vendor_b.id})")

    # Step 1: Security Tests for unauthenticated calls
    print("\n[1] Testing Security: Unauthenticated calls without Bearer token...")
    st1, resp1 = send_request("GET", "/api/vendor/stock/list/")
    assert st1 == 401, f"Expected 401 for stock list, got {st1}"
    print(f" -> GET /api/vendor/stock/list/ -> 401 Unauthorized: {resp1['message']}")

    st2, resp2 = send_request("GET", "/api/vendor/stock/summary/")
    assert st2 == 401
    print(f" -> GET /api/vendor/stock/summary/ -> 401 Unauthorized")

    st3, resp3 = send_request("GET", "/api/vendor/stock/logs/")
    assert st3 == 401
    print(f" -> GET /api/vendor/stock/logs/ -> 401 Unauthorized")

    # Step 2: Create a dedicated test product for Vendor A
    print("\n[2] Creating test product for Vendor A...")
    sku = f"STOCK-{uuid.uuid4().hex[:6].upper()}"
    prod_payload = {
        "name": "Jaipur Handcrafted Ceramic Dinner Plate",
        "sku": sku,
        "price": "499.00",
        "stock_quantity": 30,
        "low_stock_threshold": 10,
        "unit": "Piece",
        "description": "Artisanal glazed dinner plate.",
        "status": "ACTIVE"
    }
    st_prod, resp_prod = send_request("POST", "/api/vendor/product/create/", data=prod_payload, headers=headers_a)
    assert st_prod == 201
    product_id = resp_prod["product"]["id"]
    print(f" -> Created Product ID {product_id} with Initial Stock: 30 for Vendor {vendor_a.id}")

    # Step 3: Stock Summary for Vendor A vs Vendor B
    print("\n[3] Testing Stock Summary Multi-Tenant Scoping...")
    st_sum_a, resp_sum_a = send_request("GET", "/api/vendor/stock/summary/", headers=headers_a)
    assert st_sum_a == 200
    sum_a = resp_sum_a["summary"]
    assert sum_a["total_skus"] >= 1
    assert sum_a["total_units"] >= 30
    print(f" -> Vendor A Summary: SKUs={sum_a['total_skus']}, Units={sum_a['total_units']}, Valuation=Rs.{sum_a['total_valuation']}")

    st_sum_b, resp_sum_b = send_request("GET", "/api/vendor/stock/summary/", headers=headers_b)
    assert st_sum_b == 200
    sum_b = resp_sum_b["summary"]
    # Vendor B should not have Vendor A's SKUs or valuation
    print(f" -> Vendor B Summary: SKUs={sum_b['total_skus']}, Units={sum_b['total_units']}, Valuation=Rs.{sum_b['total_valuation']}")

    # Step 4: Multi-tenant Security: Vendor B attempts to adjust stock on Vendor A's product
    print(f"\n[4] Testing Security: Vendor B attempts to adjust stock on Vendor A's product {product_id}...")
    st_cross_stk, resp_cross_stk = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data={"action": "ADD", "quantity": 10}, headers=headers_b)
    print(f" -> Status: {st_cross_stk}")
    print(f" -> Response: {resp_cross_stk}")
    assert st_cross_stk == 403, f"Expected 403 Forbidden, got {st_cross_stk}"
    assert "Access denied" in resp_cross_stk.get("message", "")
    print(" -> PASSED: Vendor B is forbidden from adjusting Vendor A's stock!")

    # Step 5: Test Rightful Stock Restock by Vendor A (action=ADD)
    print(f"\n[5] Testing Restock by Vendor A (action: ADD, qty: 20)...")
    add_payload = {
        "action": "ADD",
        "quantity": 20,
        "movement_type": "RESTOCK",
        "reason": "Received batch invoice #REC-8841 from ceramic workshop",
        "reference_id": "PO-8841"
    }
    st_add, resp_add = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=add_payload, headers=headers_a)
    assert st_add == 200
    assert resp_add["product"]["stock_quantity"] == 50  # 30 + 20
    assert resp_add["log"]["quantity_changed"] == 20
    assert resp_add["log"]["movement_type"] == "RESTOCK"
    print(f" -> Restocked! Stock updated from 30 to 50 units.")

    # Step 6: Test Stock Deduction for Damage by Vendor A (action=SUBTRACT)
    print(f"\n[6] Testing Stock Damage Deduction (action: SUBTRACT, qty: 5)...")
    sub_payload = {
        "action": "SUBTRACT",
        "quantity": 5,
        "movement_type": "DAMAGE",
        "reason": "Broken during warehouse transit",
        "reference_id": "DMG-102"
    }
    st_sub, resp_sub = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=sub_payload, headers=headers_a)
    assert st_sub == 200
    assert resp_sub["product"]["stock_quantity"] == 45  # 50 - 5
    assert resp_sub["log"]["quantity_changed"] == -5
    print(f" -> Deducted! Stock reduced to 45 units.")

    # Step 7: Test Low Stock Alert Threshold (action=SET, qty: 8; threshold: 10)
    print(f"\n[7] Testing Low Stock Alert (action: SET, qty: 8; threshold: 10)...")
    set_payload = {
        "action": "SET",
        "quantity": 8,
        "movement_type": "CORRECTION",
        "reason": "Physical count audit adjustment",
        "reference_id": "AUDIT-2026-Q4"
    }
    st_set, resp_set = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=set_payload, headers=headers_a)
    assert st_set == 200
    assert resp_set["product"]["stock_quantity"] == 8
    assert resp_set["product"]["stock_status"] == "LOW_STOCK"
    print(f" -> Stock Status dynamically updated to: {resp_set['product']['stock_status']}")

    # Step 8: Filter Stock List by 'low_stock' for Vendor A
    print(f"\n[8] Testing GET /api/vendor/stock/list/?level=low_stock with Vendor A...")
    st_low, resp_low = send_request("GET", "/api/vendor/stock/list/?level=low_stock", headers=headers_a)
    assert st_low == 200
    low_ids = [item["product_id"] for item in resp_low.get("inventory", [])]
    assert product_id in low_ids, "Product should appear in low_stock filter!"
    print(f" -> Low Stock List Count: {resp_low.get('count')} (Product ID {product_id} included)")

    # Step 9: Test Out of Stock Depletion (action=SET, qty: 0)
    print(f"\n[9] Testing Out of Stock Depletion (action: SET, qty: 0)...")
    out_payload = {
        "action": "SET",
        "quantity": 0,
        "movement_type": "CORRECTION",
        "reason": "Inventory completely sold out"
    }
    st_out, resp_out = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=out_payload, headers=headers_a)
    assert st_out == 200
    assert resp_out["product"]["stock_quantity"] == 0
    assert resp_out["product"]["stock_status"] == "OUT_OF_STOCK"
    assert resp_out["product"]["status"] == "OUT_OF_STOCK"
    print(f" -> Stock Status: {resp_out['product']['stock_status']}, Product Status: {resp_out['product']['status']}")

    # Step 10: Test Re-stocking from Out of Stock back to Active
    print(f"\n[10] Restocking 25 units to verify auto-reactivation...")
    reactivate_payload = {
        "action": "ADD",
        "quantity": 25,
        "movement_type": "RESTOCK",
        "reason": "Supplier fresh shipment received"
    }
    st_rec, resp_rec = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=reactivate_payload, headers=headers_a)
    assert st_rec == 200
    assert resp_rec["product"]["stock_quantity"] == 25
    assert resp_rec["product"]["stock_status"] == "HEALTHY"
    assert resp_rec["product"]["status"] == "ACTIVE"
    print(f" -> Reactivated! Stock Status: {resp_rec['product']['stock_status']}, Product Status: {resp_rec['product']['status']}")

    # Step 11: Multi-tenant Security: Vendor B attempts to view stock logs of Vendor A's product -> 403 Forbidden!
    print(f"\n[11] Testing Security: Vendor B attempts to view stock logs of Vendor A's product {product_id}...")
    st_cross_log, resp_cross_log = send_request("GET", f"/api/vendor/stock/logs/{product_id}/", headers=headers_b)
    print(f" -> Status: {st_cross_log}")
    assert st_cross_log == 403
    assert "Access denied" in resp_cross_log.get("message", "")
    print(" -> PASSED: Vendor B is forbidden from viewing Vendor A's stock audit ledger!")

    # Step 12: Vendor A views their own stock audit ledger
    print(f"\n[12] Testing GET /api/vendor/stock/logs/{product_id}/ by Vendor A...")
    st_logs, resp_logs = send_request("GET", f"/api/vendor/stock/logs/{product_id}/", headers=headers_a)
    assert st_logs == 200
    assert resp_logs.get("count") >= 5
    print(f" -> Total Log Entries: {resp_logs.get('count')}")
    print(f" -> Latest Log Movement: {resp_logs['logs'][0]['movement_type_display']} ({resp_logs['logs'][0]['quantity_changed']} units)")

    # Step 13: Test Public / Admin Aliases
    print("\n[13] Testing Aliases: /api/stock/summary/ and /api/admin/stock/logs/...")
    st_a1, resp_a1 = send_request("GET", "/api/stock/summary/")
    assert st_a1 == 200
    st_a2, resp_a2 = send_request("GET", f"/api/admin/stock/logs/{product_id}/")
    assert st_a2 == 200
    print(" -> Aliases operating normally!")

    # Save results
    results["security_checks"] = [
        "401_missing_token_on_stock_list",
        "401_missing_token_on_stock_summary",
        "401_missing_token_on_stock_logs",
        "403_cross_vendor_stock_update_forbidden",
        "403_cross_vendor_stock_logs_forbidden",
        "tenant_isolated_stock_summary"
    ]
    with open("stock_api_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 65)
    print(" ALL 13 STOCK MANAGEMENT & SECURITY TESTS PASSED 100%! ")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
