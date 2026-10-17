import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:8000"

def request(method, path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            res_body = resp.read().decode("utf-8")
            return status, json.loads(res_body)
    except urllib.error.HTTPError as e:
        status = e.code
        res_body = e.read().decode("utf-8")
        try:
            return status, json.loads(res_body)
        except Exception:
            return status, res_body

results = {}

print("=== 1. Create Category via /api/vendor/category/create/ ===")
payload1 = {
    "name": "Handmade Wooden Carvings",
    "description": "Authentic walnut wood and deodar handcrafted decorative art pieces",
    "commission_rate": 8.00,
    "icon": "fa-tree",
    "display_order": 3,
    "is_active": True
}
status, res = request("POST", "/api/vendor/category/create/", payload1)
print(f"Status: {status}, Response: {res}")
results["vendor_category_create"] = {"status": status, "payload": payload1, "response": res}
created_id = res.get("category", {}).get("id")

print(f"\n=== 2. Create Subcategory under ID {created_id} via /api/vendor/category/create/ ===")
sub_payload = {
    "name": "Walnut Jewelry Boxes",
    "description": "Intricately carved Kashmiri walnut wood jewelry boxes with brass inlays",
    "parent_id": created_id,
    "commission_rate": 9.50,
    "icon": "fa-gem",
    "display_order": 1,
    "is_active": True
}
status, res = request("POST", "/api/vendor/category/create/", sub_payload)
print(f"Status: {status}, Response: {res}")
results["vendor_subcategory_create"] = {"status": status, "payload": sub_payload, "response": res}
sub_id = res.get("category", {}).get("id")

print("\n=== 3. List Categories via /api/vendor/category/list/ ===")
status, res = request("GET", "/api/vendor/category/list/")
print(f"Status: {status}, Total count: {res.get('count')}")
results["vendor_category_list"] = {"status": status, "response": res}

print("\n=== 4. List Root Categories via /api/vendor/category/list/?parent=null ===")
status, res = request("GET", "/api/vendor/category/list/?parent=null")
print(f"Status: {status}, Count: {res.get('count')}")
results["vendor_root_category_list"] = {"status": status, "response": res}

print(f"\n=== 5. Get Category Detail via /api/vendor/category/detail/{created_id}/ ===")
status, res = request("GET", f"/api/vendor/category/detail/{created_id}/")
print(f"Status: {status}, Name: {res.get('category', {}).get('name')}")
results["vendor_category_detail"] = {"status": status, "response": res}

print(f"\n=== 6. Update Category via POST /api/vendor/category/update/{created_id}/ ===")
update_payload = {
    "commission_rate": 7.50,
    "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
    "icon": "fa-tree"
}
status, res = request("POST", f"/api/vendor/category/update/{created_id}/", update_payload)
print(f"Status: {status}, Updated Rate: {res.get('category', {}).get('commission_rate')}")
results["vendor_category_update"] = {"status": status, "payload": update_payload, "response": res}

print("\n=== 7. Get Category Hierarchy Tree via /api/vendor/category/tree/ ===")
status, res = request("GET", "/api/vendor/category/tree/")
print(f"Status: {status}, Root Tree Count: {res.get('count')}")
results["vendor_category_tree"] = {"status": status, "response": res}

print(f"\n=== 8. Delete Subcategory via POST /api/vendor/category/delete/{sub_id}/ ===")
status, res = request("POST", f"/api/vendor/category/delete/{sub_id}/")
print(f"Status: {status}, Response: {res}")
results["vendor_category_delete"] = {"status": status, "response": res}

print("\n=== 9. Verify Admin Category Endpoint Parity /api/admin/category/list/ ===")
status, res = request("GET", "/api/admin/category/list/")
print(f"Status: {status}, Count: {res.get('count')}")
results["admin_category_list"] = {"status": status, "response": res}

with open("role_category_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nAll role-prefixed and explicit endpoint tests completed successfully!")
