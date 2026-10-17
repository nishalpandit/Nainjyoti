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

print("=== 1. Create Category: Handicrafts & Handlooms ===")
payload1 = {
    "name": "Handicrafts & Handlooms",
    "status": "ACTIVE"
}
status, res = request("POST", "/api/vendor/category/create/", payload1)
print(f"Status: {status}, Response: {res}")
results["create_category_1"] = {"status": status, "payload": payload1, "response": res}
cat1_id = res.get("category", {}).get("id")

print("\n=== 2. Create Category: Spices & Dry Fruits ===")
payload2 = {
    "name": "Spices & Dry Fruits",
    "status": "ACTIVE"
}
status, res = request("POST", "/api/vendor/category/create/", payload2)
print(f"Status: {status}, Response: {res}")
results["create_category_2"] = {"status": status, "payload": payload2, "response": res}
cat2_id = res.get("category", {}).get("id")

print("\n=== 3. List All Categories ===")
status, res = request("GET", "/api/vendor/category/list/")
print(f"Status: {status}, Count: {res.get('count')}")
results["list_categories"] = {"status": status, "response": res}

print(f"\n=== 4. Get Category Details (ID: {cat1_id}) ===")
status, res = request("GET", f"/api/vendor/category/detail/{cat1_id}/")
print(f"Status: {status}, Response: {res}")
results["category_detail"] = {"status": status, "response": res}

print(f"\n=== 5. Update Category (ID: {cat1_id}) to INACTIVE ===")
update_payload = {
    "status": "INACTIVE"
}
status, res = request("POST", f"/api/vendor/category/update/{cat1_id}/", update_payload)
print(f"Status: {status}, Response: {res}")
results["update_category"] = {"status": status, "payload": update_payload, "response": res}

print(f"\n=== 6. Delete Category (ID: {cat2_id}) ===")
status, res = request("POST", f"/api/vendor/category/delete/{cat2_id}/")
print(f"Status: {status}, Response: {res}")
results["delete_category"] = {"status": status, "response": res}

print("\n=== 7. List Active Categories Only (?status=ACTIVE) ===")
status, res = request("GET", "/api/vendor/category/list/?status=ACTIVE")
print(f"Status: {status}, Count: {res.get('count')}")
results["list_active_categories"] = {"status": status, "response": res}

with open("master_category_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nMaster Category API tests completed successfully!")
