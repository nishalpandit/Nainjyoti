import urllib.request
import urllib.parse
import urllib.error
import json
import uuid

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

def run_tests():
    results = {}
    print("=" * 65)
    print(" STARTING STOCK MANAGEMENT & AUDIT LEDGER TEST SUITE ")
    print("=" * 65)

    # Step 1: Ensure we have a product for testing stock
    print("\n[1] Preparing a dedicated test product...")
    sku = f"STOCK-TEST-{uuid.uuid4().hex[:6].upper()}"
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
    st, resp = send_request("POST", "/api/vendor/product/create/", data=prod_payload)
    assert st == 201, f"Failed to create product: {resp}"
    product_id = resp["product"]["id"]
    print(f" -> Created Test Product ID {product_id} with Initial Stock: 30")

    # Step 2: Test Stock Summary API
    print("\n[2] Testing GET /api/vendor/stock/summary/...")
    st_sum, resp_sum = send_request("GET", "/api/vendor/stock/summary/")
    print(f" -> Status: {st_sum}")
    print(f" -> Response Summary: {json.dumps(resp_sum.get('summary'), indent=2)}")
    results["1_stock_summary"] = {
        "status_code": st_sum,
        "response": resp_sum
    }
    assert st_sum == 200
    summary = resp_sum["summary"]
    assert summary["total_skus"] >= 1
    assert summary["total_units"] >= 30
    assert summary["total_valuation"] > 0

    # Step 3: Test Stock List API (All levels)
    print("\n[3] Testing GET /api/vendor/stock/list/...")
    st_list, resp_list = send_request("GET", "/api/vendor/stock/list/")
    print(f" -> Status: {st_list}, Total items: {resp_list.get('count')}")
    results["2_stock_list_all"] = {
        "status_code": st_list,
        "count": resp_list.get("count")
    }
    assert st_list == 200
    assert resp_list.get("count") >= 1

    # Step 4: Test Stock Restock (action=ADD)
    print(f"\n[4] Testing POST /api/vendor/stock/update/{product_id}/ (action: ADD, qty: 20)...")
    add_payload = {
        "action": "ADD",
        "quantity": 20,
        "movement_type": "RESTOCK",
        "reason": "Received batch invoice #REC-8841 from ceramic workshop",
        "reference_id": "PO-8841"
    }
    st_add, resp_add = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=add_payload)
    print(f" -> Status: {st_add}")
    print(f" -> Message: {resp_add.get('message')}")
    results["3_stock_add_restock"] = {
        "status_code": st_add,
        "response": resp_add
    }
    assert st_add == 200
    prod_data = resp_add["product"]
    assert prod_data["stock_quantity"] == 50  # 30 + 20
    assert resp_add["log"]["quantity_changed"] == 20
    assert resp_add["log"]["movement_type"] == "RESTOCK"

    # Step 5: Test Stock Deduction for Damage (action=SUBTRACT)
    print(f"\n[5] Testing POST /api/vendor/stock/update/{product_id}/ (action: SUBTRACT, qty: 5)...")
    sub_payload = {
        "action": "SUBTRACT",
        "quantity": 5,
        "movement_type": "DAMAGE",
        "reason": "Broken during warehouse transit",
        "reference_id": "DMG-102"
    }
    st_sub, resp_sub = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=sub_payload)
    print(f" -> Status: {st_sub}")
    print(f" -> Message: {resp_sub.get('message')}")
    results["4_stock_subtract_damage"] = {
        "status_code": st_sub,
        "response": resp_sub
    }
    assert st_sub == 200
    assert resp_sub["product"]["stock_quantity"] == 45  # 50 - 5
    assert resp_sub["log"]["quantity_changed"] == -5
    assert resp_sub["log"]["movement_type"] == "DAMAGE"

    # Step 6: Test Low Stock Alert Threshold (action=SET, qty: 8; threshold is 10)
    print(f"\n[6] Testing Low Stock Alert (action: SET, qty: 8; threshold: 10)...")
    set_payload = {
        "action": "SET",
        "quantity": 8,
        "movement_type": "CORRECTION",
        "reason": "Physical count audit adjustment",
        "reference_id": "AUDIT-2026-Q4"
    }
    st_set, resp_set = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=set_payload)
    assert st_set == 200
    assert resp_set["product"]["stock_quantity"] == 8
    assert resp_set["product"]["stock_status"] == "LOW_STOCK"
    print(f" -> Stock Status dynamically updated to: {resp_set['product']['stock_status']}")
    results["5_stock_low_stock_status"] = {
        "status_code": st_set,
        "stock_status": resp_set["product"]["stock_status"],
        "stock_quantity": resp_set["product"]["stock_quantity"]
    }

    # Step 7: Filter Stock List by 'low_stock'
    print(f"\n[7] Testing GET /api/vendor/stock/list/?level=low_stock...")
    st_low, resp_low = send_request("GET", "/api/vendor/stock/list/?level=low_stock")
    assert st_low == 200
    low_ids = [item["product_id"] for item in resp_low.get("inventory", [])]
    assert product_id in low_ids, "Product should appear in low_stock filter!"
    print(f" -> Low Stock List Count: {resp_low.get('count')} (Product ID {product_id} included)")
    results["6_stock_list_low_stock_filter"] = {
        "status_code": st_low,
        "count": resp_low.get("count")
    }

    # Step 8: Test Out of Stock Depletion (action=SET, qty: 0)
    print(f"\n[8] Testing Out of Stock Depletion (action: SET, qty: 0)...")
    out_payload = {
        "action": "SET",
        "quantity": 0,
        "movement_type": "CORRECTION",
        "reason": "Inventory completely sold out"
    }
    st_out, resp_out = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=out_payload)
    assert st_out == 200
    assert resp_out["product"]["stock_quantity"] == 0
    assert resp_out["product"]["stock_status"] == "OUT_OF_STOCK"
    assert resp_out["product"]["status"] == "OUT_OF_STOCK"
    print(f" -> Stock Status: {resp_out['product']['stock_status']}, Product Status: {resp_out['product']['status']}")
    results["7_stock_out_of_stock"] = {
        "status_code": st_out,
        "stock_status": resp_out["product"]["stock_status"]
    }

    # Step 9: Test Re-stocking from Out of Stock back to Active
    print(f"\n[9] Restocking 25 units to verify auto-reactivation...")
    reactivate_payload = {
        "action": "ADD",
        "quantity": 25,
        "movement_type": "RESTOCK",
        "reason": "Supplier fresh shipment received"
    }
    st_rec, resp_rec = send_request("POST", f"/api/vendor/stock/update/{product_id}/", data=reactivate_payload)
    assert st_rec == 200
    assert resp_rec["product"]["stock_quantity"] == 25
    assert resp_rec["product"]["stock_status"] == "HEALTHY"
    assert resp_rec["product"]["status"] == "ACTIVE"
    print(f" -> Reactivated! Stock Status: {resp_rec['product']['stock_status']}, Product Status: {resp_rec['product']['status']}")

    # Step 10: Test Stock Audit Logs API
    print(f"\n[10] Testing GET /api/vendor/stock/logs/{product_id}/...")
    st_logs, resp_logs = send_request("GET", f"/api/vendor/stock/logs/{product_id}/")
    print(f" -> Status: {st_logs}, Total Log Entries: {resp_logs.get('count')}")
    assert st_logs == 200
    assert resp_logs.get("count") >= 5  # Initial + Restock + Damage + Set(8) + Set(0) + Restock(25)
    print(f" -> Latest Log Movement: {resp_logs['logs'][0]['movement_type_display']} ({resp_logs['logs'][0]['quantity_changed']} units)")
    results["8_stock_movement_logs"] = {
        "status_code": st_logs,
        "count": resp_logs.get("count"),
        "logs": resp_logs.get("logs")
    }

    # Step 11: Test General / Admin Aliases
    print("\n[11] Testing Aliases: /api/stock/summary/ and /api/admin/stock/logs/...")
    st_a1, resp_a1 = send_request("GET", "/api/stock/summary/")
    assert st_a1 == 200
    st_a2, resp_a2 = send_request("GET", f"/api/admin/stock/logs/{product_id}/")
    assert st_a2 == 200
    print(" -> Aliases verified successfully!")

    # Save test results to JSON
    with open("stock_api_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 65)
    print(" ALL 11 STOCK MANAGEMENT API TESTS PASSED 100% SUCCESSFULLY! ")
    print(" Full logs written to: stock_api_test_results.json")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
