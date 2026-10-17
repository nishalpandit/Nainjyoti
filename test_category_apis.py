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

# Clean up any previous test categories for fresh run
status, existing_list = request("GET", "/api/categories/?all=true")
existing_map = {c["name"]: c["id"] for c in existing_list.get("categories", [])}

print("=== 1. Create or Retrieve Parent Category: Fashion & Textiles ===")
cat1_payload = {
    "name": "Fashion & Textiles",
    "description": "Ethnic wear, fabrics, apparel, handcrafted garments and modern fashion",
    "commission_rate": 10.00,
    "icon": "fa-shirt",
    "display_order": 1,
    "is_active": True
}
if "Fashion & Textiles" in existing_map:
    fashion_id = existing_map["Fashion & Textiles"]
    status, res = request("GET", f"/api/categories/{fashion_id}/")
    print(f"Existing Category Found (ID: {fashion_id})")
else:
    status, res = request("POST", "/api/categories/", cat1_payload)
    fashion_id = res.get("category", {}).get("id")
    print(f"Created (Status: {status}, ID: {fashion_id})")
results["create_parent_category"] = {"status": status, "payload": cat1_payload, "response": res}

print("\n=== 2. Create or Retrieve Parent Category: Electronics & Appliances ===")
cat2_payload = {
    "name": "Electronics & Appliances",
    "description": "Smartphones, home appliances, wearable devices and smart gadgets",
    "commission_rate": 7.50,
    "icon": "fa-laptop",
    "display_order": 2,
    "is_active": True
}
if "Electronics & Appliances" in existing_map:
    elec_id = existing_map["Electronics & Appliances"]
    status, res = request("GET", f"/api/categories/{elec_id}/")
    print(f"Existing Category Found (ID: {elec_id})")
else:
    status, res = request("POST", "/api/categories/", cat2_payload)
    elec_id = res.get("category", {}).get("id")
    print(f"Created (Status: {status}, ID: {elec_id})")
results["create_electronics_category"] = {"status": status, "payload": cat2_payload, "response": res}

print(f"\n=== 3. Create or Retrieve Subcategory under Fashion (Parent ID: {fashion_id}) ===")
sub1_payload = {
    "name": "Kashmiri Shawls & Stoles",
    "description": "Authentic hand-woven Pashmina, Cashmere and embroidered woollen shawls",
    "parent_id": fashion_id,
    "commission_rate": 12.00,
    "icon": "fa-vest",
    "display_order": 1,
    "is_active": True
}
if "Kashmiri Shawls & Stoles" in existing_map:
    sub1_id = existing_map["Kashmiri Shawls & Stoles"]
    status, res = request("GET", f"/api/categories/{sub1_id}/")
    print(f"Existing Subcategory Found (ID: {sub1_id})")
else:
    status, res = request("POST", "/api/categories/", sub1_payload)
    sub1_id = res.get("category", {}).get("id")
    print(f"Created (Status: {status}, ID: {sub1_id})")
results["create_subcategory"] = {"status": status, "payload": sub1_payload, "response": res}

print(f"\n=== 4. Create or Retrieve Second Subcategory under Fashion (Parent ID: {fashion_id}) ===")
sub2_payload = {
    "name": "Handcrafted Silk Sarees",
    "description": "Traditional banarasi, chanderi, and pure silk heritage sarees",
    "parent_id": fashion_id,
    "commission_rate": 10.00,
    "icon": "fa-ribbon",
    "display_order": 2,
    "is_active": True
}
if "Handcrafted Silk Sarees" in existing_map:
    sub2_id = existing_map["Handcrafted Silk Sarees"]
    status, res = request("GET", f"/api/categories/{sub2_id}/")
    print(f"Existing Subcategory Found (ID: {sub2_id})")
else:
    status, res = request("POST", "/api/categories/", sub2_payload)
    sub2_id = res.get("category", {}).get("id")
    print(f"Created (Status: {status}, ID: {sub2_id})")
results["create_second_subcategory"] = {"status": status, "payload": sub2_payload, "response": res}

print("\n=== 5. List All Categories ===")
status, res = request("GET", "/api/categories/")
print(f"Status: {status}, Total count: {res.get('count')}")
results["list_all_categories"] = {"status": status, "response": res}

print("\n=== 6. List Root Categories Only (?parent=null) ===")
status, res = request("GET", "/api/categories/?parent=null")
print(f"Status: {status}, Count: {res.get('count')}")
results["list_root_categories"] = {"status": status, "response": res}

print(f"\n=== 7. List Subcategories for Parent ({fashion_id}) ===")
status, res = request("GET", f"/api/categories/?parent_id={fashion_id}")
print(f"Status: {status}, Count: {res.get('count')}")
results["list_subcategories_by_parent"] = {"status": status, "response": res}

print("\n=== 8. Get Hierarchical Category Tree (/api/categories/tree/) ===")
status, res = request("GET", "/api/categories/tree/")
print(f"Status: {status}, Count: {res.get('count')}")
results["category_tree"] = {"status": status, "response": res}

print(f"\n=== 9. Get Category Details by ID (/api/categories/{fashion_id}/) ===")
status, res = request("GET", f"/api/categories/{fashion_id}/")
print(f"Status: {status}, Name: {res.get('category', {}).get('name')}")
results["category_details_by_id"] = {"status": status, "response": res}

print("\n=== 10. Get Category Details by Slug (/api/categories/slug/fashion-textiles/) ===")
status, res = request("GET", "/api/categories/slug/fashion-textiles/")
print(f"Status: {status}, Name: {res.get('category', {}).get('name')}")
results["category_details_by_slug"] = {"status": status, "response": res}

print(f"\n=== 11. Update Category (/api/categories/{fashion_id}/) ===")
update_payload = {
    "commission_rate": 9.50,
    "description": "Updated: Premium ethnic wear, fabrics, apparel, Kashmiri shawls and modern fashion",
    "icon": "fa-shirt"
}
status, res = request("PUT", f"/api/categories/{fashion_id}/", update_payload)
print(f"Status: {status}, Updated Rate: {res.get('category', {}).get('commission_rate')}")
results["update_category"] = {"status": status, "payload": update_payload, "response": res}

print("\n=== 12. Create Temporary Category for Deletion Test ===")
temp_payload = {
    "name": "Temporary Sample Category",
    "description": "Category created to test delete endpoint",
    "commission_rate": 5.00
}
status, res = request("POST", "/api/categories/", temp_payload)
temp_id = res.get("category", {}).get("id")
print(f"Temporary category created with ID: {temp_id}")

print(f"\n=== 13. Soft Delete Category (?soft=true) ===")
status, res = request("DELETE", f"/api/categories/{temp_id}/?soft=true")
print(f"Status: {status}, Response: {res}")
results["soft_delete_category"] = {"status": status, "response": res}

print(f"\n=== 14. Permanent Delete Category ===")
status, res = request("DELETE", f"/api/categories/{temp_id}/")
print(f"Status: {status}, Response: {res}")
results["permanent_delete_category"] = {"status": status, "response": res}

print("\n=== 15. Validation Error: Duplicate Category Name ===")
status, res = request("POST", "/api/categories/", {"name": "Fashion & Textiles"})
print(f"Status: {status}, Response: {res}")
results["duplicate_validation_error"] = {"status": status, "response": res}

with open("category_api_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nAll test scenarios completed successfully! Results written to category_api_test_results.json")
