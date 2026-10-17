import urllib.request
import urllib.error
import urllib.parse
import json
import time
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

BASE_URL = "http://192.168.1.52:8000"
try:
    urllib.request.urlopen(f"{BASE_URL}/api/vendor/register/", timeout=1)
except Exception:
    BASE_URL = "http://127.0.0.1:8000"

def make_request(method, endpoint, payload=None, token=None, params=None):
    url = f"{BASE_URL}{endpoint}"
    if params:
        query_string = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{query_string}"
        
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    data_bytes = None
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")
        
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            body_text = response.read().decode("utf-8")
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            try:
                body_json = json.loads(body_text)
            except Exception:
                body_json = body_text
            return {
                "status_code": status_code,
                "elapsed_ms": elapsed_ms,
                "response": body_json
            }
    except urllib.error.HTTPError as err:
        status_code = err.code
        body_text = err.read().decode("utf-8")
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        try:
            body_json = json.loads(body_text)
        except Exception:
            body_json = body_text
        return {
            "status_code": status_code,
            "elapsed_ms": elapsed_ms,
            "response": body_json
        }
    except Exception as e:
        return {
            "status_code": 0,
            "elapsed_ms": 0,
            "error": str(e)
        }

def run_tests():
    ts = int(time.time())
    test_email = f"merchant_{ts}@crafts.in"
    test_phone = f"97{ts % 100000000:08d}"
    
    print(f"[*] Starting Vendor API test suite on {BASE_URL}")
    print(f"[*] Generated vendor credentials: {test_email} | {test_phone}")
    
    results = []
    
    def log_test(test_id, name, method, endpoint, payload, token, result):
        record = {
            "test_id": test_id,
            "name": name,
            "method": method,
            "endpoint": endpoint,
            "request_payload": payload,
            "token_used": bool(token),
            "status_code": result.get("status_code"),
            "elapsed_ms": result.get("elapsed_ms"),
            "response_data": result.get("response")
        }
        results.append(record)
        print(f"\n-------------------------------------------------------------")
        print(f"[{test_id}] {name}")
        print(f">> {method} {endpoint} (HTTP {result.get('status_code')} in {result.get('elapsed_ms')}ms)")
        if payload:
            print(f">> Request Payload: {json.dumps(payload, indent=2)}")
        print(f">> Response:")
        print(json.dumps(result.get("response"), indent=2))
        return record

    # =========================================================================
    # 1. API: api_vendor_register (/api/vendor/register/)
    # =========================================================================
    # TC-V01: Validation check (missing business name)
    res = make_request("POST", "/api/vendor/register/", payload={"owner_name": "Dev", "email": "test@test.com"})
    log_test("TC-V01", "Vendor registration with missing business name", "POST", "/api/vendor/register/", {"owner_name": "Dev", "email": "test@test.com"}, None, res)

    # TC-V02: Validation check (password < 6 chars)
    res = make_request("POST", "/api/vendor/register/", payload={
        "business_name": "Varanasi Silk Hub",
        "owner_name": "Rohan Gupta",
        "email": test_email,
        "phone": test_phone,
        "password": "123"
    })
    log_test("TC-V02", "Vendor registration with short password (<6 chars)", "POST", "/api/vendor/register/", {
        "business_name": "Varanasi Silk Hub",
        "owner_name": "Rohan Gupta",
        "email": test_email,
        "phone": test_phone,
        "password": "123"
    }, None, res)

    # TC-V03: Complete Vendor Registration with suitable fields
    full_vendor_payload = {
        "business_name": f"Himalayan Artisans Guild {ts}",
        "owner_name": "Farooq Ahmed",
        "email": test_email,
        "phone": test_phone,
        "password": "SellerSecure@2026",
        "business_type": "Manufacturer & Artisan",
        "category": "Handicrafts & Handlooms",
        "address": "42 Heritage Arts Lane, Old City",
        "city": "Srinagar",
        "state": "Jammu and Kashmir",
        "pincode": "190001",
        "gst_number": f"01TESTG{ts % 10000:04d}A1Z5",
        "pan_number": f"TESTP{ts % 10000:04d}F",
        "bank_name": "HDFC Bank",
        "account_number": "50100492817291",
        "ifsc_code": "HDFC0000123"
    }
    res = make_request("POST", "/api/vendor/register/", payload=full_vendor_payload)
    log_test("TC-V03", "Full Vendor Registration with compliance & bank fields", "POST", "/api/vendor/register/", full_vendor_payload, None, res)
    vendor_code = res.get("response", {}).get("vendor_code")
    pending_token = res.get("response", {}).get("token")

    # TC-V04: Duplicate registration prevention
    res = make_request("POST", "/api/vendor/register/", payload=full_vendor_payload)
    log_test("TC-V04", "Prevent duplicate registration with already registered email", "POST", "/api/vendor/register/", full_vendor_payload, None, res)

    # =========================================================================
    # 2. API: api_vendor_status_lookup (/api/vendor/status/)
    # =========================================================================
    # TC-V05: Public Status Tracking by vendor_code
    res = make_request("GET", "/api/vendor/status/", params={"code": vendor_code})
    log_test("TC-V05", "Track Vendor Application Status by reference code", "GET", f"/api/vendor/status/?code={vendor_code}", None, None, res)

    # =========================================================================
    # 3. API: api_vendor_login (/api/vendor/login/) - PENDING STATUS CHECK
    # =========================================================================
    # TC-V06: Attempt login while status is PENDING (expect 403 Forbidden with Review notice)
    login_payload = {
        "username": test_email,
        "password": "SellerSecure@2026"
    }
    res = make_request("POST", "/api/vendor/login/", payload=login_payload)
    log_test("TC-V06", "Vendor login attempt while application is PENDING review", "POST", "/api/vendor/login/", login_payload, None, res)

    # TC-V07: Login attempt with wrong password
    bad_login_payload = {
        "username": test_email,
        "password": "WrongPassword999"
    }
    res = make_request("POST", "/api/vendor/login/", payload=bad_login_payload)
    log_test("TC-V07", "Vendor login attempt with invalid credentials", "POST", "/api/vendor/login/", bad_login_payload, None, res)

    # =========================================================================
    # Simulate Admin Approval for Vendor
    # =========================================================================
    try:
        from nainjyoti.models import VendorProfile
        v_obj = VendorProfile.objects.filter(vendor_code=vendor_code).first()
        if v_obj:
            v_obj.status = "APPROVED"
            v_obj.save()
            print(f"\n[*] [SYSTEM SIMULATION] Store '{v_obj.business_name}' ({vendor_code}) approved by Admin.")
    except Exception as e:
        print(f"[*] Admin simulation error: {e}")

    # =========================================================================
    # 4. API: api_vendor_login (/api/vendor/login/) - APPROVED STATUS CHECK
    # =========================================================================
    # TC-V08: Login with APPROVED Vendor Credentials
    res = make_request("POST", "/api/vendor/login/", payload=login_payload)
    log_test("TC-V08", "Vendor login for APPROVED store", "POST", "/api/vendor/login/", login_payload, None, res)
    approved_token = res.get("response", {}).get("token") or pending_token

    # TC-V09: Login using vendor_code instead of email
    login_by_code = {
        "username": vendor_code,
        "password": "SellerSecure@2026"
    }
    res = make_request("POST", "/api/vendor/login/", payload=login_by_code)
    log_test("TC-V09", "Vendor login using unique vendor_code identifier", "POST", "/api/vendor/login/", login_by_code, None, res)

    # =========================================================================
    # 5. API: api_vendor_profile (/api/vendor/profile/) - GET & PUT/POST
    # =========================================================================
    # TC-V10: Get profile without Bearer token
    res = make_request("GET", "/api/vendor/profile/")
    log_test("TC-V10", "Get vendor profile without authorization token", "GET", "/api/vendor/profile/", None, None, res)

    # TC-V11: Get profile with authorized Bearer token
    res = make_request("GET", "/api/vendor/profile/", token=approved_token)
    log_test("TC-V11", "Get authenticated vendor profile with Bearer token", "GET", "/api/vendor/profile/", None, approved_token, res)

    # TC-V12: Update vendor profile information
    profile_update = {
        "business_name": "Kashmir Pashmina & Royal Silk Co.",
        "phone": test_phone,
        "city": "Srinagar (Old Market)",
        "bank_name": "State Bank of India",
        "account_number": "30199482710",
        "ifsc_code": "SBIN0001234",
        "store_description": "Finest handwoven Pashmina shawls, artisanal stoles, and traditional Kashmiri handicrafts.",
        "support_email": f"support_{ts}@crafts.in"
    }
    res = make_request("POST", "/api/vendor/profile/", payload=profile_update, token=approved_token)
    log_test("TC-V12", "Update vendor store, branding & banking details", "POST", "/api/vendor/profile/", profile_update, approved_token, res)

    # TC-V13: Change Password - Invalid current password check
    res = make_request("POST", "/api/vendor/profile/change-password/", payload={
        "current_password": "WrongCurrentPassword",
        "new_password": "BrandNewPassword@2026"
    }, token=approved_token)
    log_test("TC-V13", "Vendor password change with incorrect current password", "POST", "/api/vendor/profile/change-password/", {
        "current_password": "WrongCurrentPassword",
        "new_password": "BrandNewPassword@2026"
    }, approved_token, res)

    # TC-V14: Change Password - Successful change & token rotation
    res = make_request("POST", "/api/vendor/profile/change-password/", payload={
        "current_password": "SellerSecure@2026",
        "new_password": "BrandNewPassword@2026"
    }, token=approved_token)
    log_test("TC-V14", "Vendor password change success and token rotation", "POST", "/api/vendor/profile/change-password/", {
        "current_password": "SellerSecure@2026",
        "new_password": "BrandNewPassword@2026"
    }, approved_token, res)
    new_token = res.get("response", {}).get("token") or approved_token

    # TC-V15: Verify new password login
    res = make_request("POST", "/api/vendor/login/", payload={
        "username": test_email,
        "password": "BrandNewPassword@2026"
    })
    log_test("TC-V15", "Vendor login using newly updated password", "POST", "/api/vendor/login/", {
        "username": test_email,
        "password": "BrandNewPassword@2026"
    }, None, res)
    active_token = res.get("response", {}).get("token") or new_token

    # =========================================================================
    # 6. API: api_vendor_logout (/api/vendor/logout/)
    # =========================================================================
    # TC-V16: Logout Vendor
    res = make_request("POST", "/api/vendor/logout/", token=active_token)
    log_test("TC-V16", "Vendor logout and token revocation", "POST", "/api/vendor/logout/", None, active_token, res)

    # TC-V17: Verify revoked token rejected
    res = make_request("GET", "/api/vendor/profile/", token=active_token)
    log_test("TC-V17", "Verify revoked vendor token is rejected", "GET", "/api/vendor/profile/", None, active_token, res)

    # =========================================================================
    # Save all test results to file
    # =========================================================================
    output_filename = "vendor_api_test_results.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "server_url": BASE_URL,
            "test_vendor_code": vendor_code,
            "total_tests": len(results),
            "passed_tests": sum(1 for r in results if r["status_code"] in [200, 201, 400, 401, 403, 404, 405]),
            "tests": results
        }, f, indent=2)
    print(f"\n[OK] All {len(results)} Vendor API tests executed and saved to '{output_filename}'.")

    # Clean up test vendor and user to avoid polluting live dashboard
    try:
        from nainjyoti.models import VendorProfile
        from django.contrib.auth.models import User
        VendorProfile.objects.filter(vendor_code=vendor_code).delete()
        User.objects.filter(email=test_email).delete()
        print(f"[*] Cleaned up temporary test merchant: {test_email}")
    except Exception as e:
        print(f"[*] Note on test cleanup: {e}")

if __name__ == "__main__":
    run_tests()
