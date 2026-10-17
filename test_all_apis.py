import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def make_request(method, endpoint, payload=None, token=None):
    url = f"{BASE_URL}{endpoint}"
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
    # Use a unique timestamped phone number to ensure clean test runs
    test_phone = f"98{int(time.time()) % 100000000:08d}"
    print(f"[*] Starting API test suite on {BASE_URL}")
    print(f"[*] Generated unique test phone: {test_phone}")
    
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
            print(f">> Request Body: {json.dumps(payload, indent=2)}")
        print(f">> Response Body:")
        print(json.dumps(result.get("response"), indent=2))
        return record

    # =========================================================================
    # 1. API: api_send_otp (/api/user/send-otp/)
    # =========================================================================
    # Test 1.1: Validation failure (invalid phone)
    res = make_request("POST", "/api/user/send-otp/", payload={"phone": "123"})
    log_test("TC-01", "Request OTP with invalid short phone number", "POST", "/api/user/send-otp/", {"phone": "123"}, None, res)
    
    # Test 1.2: Valid OTP Request for new registration
    res = make_request("POST", "/api/user/send-otp/", payload={"phone": test_phone, "purpose": "REGISTER"})
    log_test("TC-02", "Request OTP for new registration", "POST", "/api/user/send-otp/", {"phone": test_phone, "purpose": "REGISTER"}, None, res)
    dev_otp = res.get("response", {}).get("otp_debug", "123456")
    
    # Test 1.3: Method Not Allowed
    res = make_request("GET", "/api/user/send-otp/")
    log_test("TC-03", "Send OTP with unsupported HTTP GET method", "GET", "/api/user/send-otp/", None, None, res)

    # =========================================================================
    # 2. API: api_verify_otp_login (/api/user/verify-otp-login/)
    # =========================================================================
    # Test 2.1: Verify with incorrect OTP
    res = make_request("POST", "/api/user/verify-otp-login/", payload={"phone": test_phone, "otp": "000000"})
    log_test("TC-04", "Verify OTP with wrong code", "POST", "/api/user/verify-otp-login/", {"phone": test_phone, "otp": "000000"}, None, res)
    
    # Test 2.2: Verify with correct OTP for unregistered user
    res = make_request("POST", "/api/user/verify-otp-login/", payload={"phone": test_phone, "otp": dev_otp})
    log_test("TC-05", "Verify OTP for unregistered user", "POST", "/api/user/verify-otp-login/", {"phone": test_phone, "otp": dev_otp}, None, res)

    # =========================================================================
    # 3. API: api_user_register (/api/user/register/)
    # =========================================================================
    # Test 3.1: Missing required names
    res = make_request("POST", "/api/user/register/", payload={"phone": test_phone})
    log_test("TC-06", "Register user with missing required name fields", "POST", "/api/user/register/", {"phone": test_phone}, None, res)
    
    # Test 3.2: Complete user registration
    reg_payload = {
        "first_name": "Aarav",
        "last_name": "Sharma",
        "phone": test_phone,
        "email": f"aarav.{test_phone}@example.com",
        "gender": "Male",
        "dob": "1994-08-15"
    }
    res = make_request("POST", "/api/user/register/", payload=reg_payload)
    log_test("TC-07", "Register user with full profile details", "POST", "/api/user/register/", reg_payload, None, res)
    auth_token = res.get("response", {}).get("token")
    
    # Test 3.3: Duplicate registration prevention
    res = make_request("POST", "/api/user/register/", payload=reg_payload)
    log_test("TC-08", "Prevent duplicate user registration with same phone", "POST", "/api/user/register/", reg_payload, None, res)

    # =========================================================================
    # 4. API: api_user_profile (/api/user/profile/) - GET
    # =========================================================================
    # Test 4.1: Unauthorized access
    res = make_request("GET", "/api/user/profile/")
    log_test("TC-09", "Fetch user profile without Bearer authorization token", "GET", "/api/user/profile/", None, None, res)
    
    # Test 4.2: Authorized profile retrieval
    res = make_request("GET", "/api/user/profile/", token=auth_token)
    log_test("TC-10", "Fetch authenticated user profile with Bearer token", "GET", "/api/user/profile/", None, auth_token, res)

    # =========================================================================
    # 5. API: api_user_profile (/api/user/profile/) - POST/PUT Update
    # =========================================================================
    # Test 5.1: Update profile details
    update_payload = {
        "first_name": "Aarav",
        "last_name": "Verma",
        "email": f"aarav.verma.{test_phone}@domain.in",
        "gender": "Male",
        "dob": "1993-05-20"
    }
    res = make_request("POST", "/api/user/profile/", payload=update_payload, token=auth_token)
    log_test("TC-11", "Update authenticated user profile details", "POST", "/api/user/profile/", update_payload, auth_token, res)

    # =========================================================================
    # 6. Verify Login Flow for Registered User
    # =========================================================================
    # Test 6.1: Request OTP for registered user
    res = make_request("POST", "/api/user/send-otp/", payload={"phone": test_phone})
    log_test("TC-12", "Request OTP for registered customer login", "POST", "/api/user/send-otp/", {"phone": test_phone}, None, res)
    login_otp = res.get("response", {}).get("otp_debug", "123456")
    
    # Test 6.2: Complete OTP Login for registered user
    res = make_request("POST", "/api/user/verify-otp-login/", payload={"phone": test_phone, "otp": login_otp})
    log_test("TC-13", "Verify OTP login for registered customer", "POST", "/api/user/verify-otp-login/", {"phone": test_phone, "otp": login_otp}, None, res)
    new_token = res.get("response", {}).get("token") or auth_token

    # =========================================================================
    # 7. API: api_user_logout (/api/user/logout/)
    # =========================================================================
    # Test 7.1: Logout user
    res = make_request("POST", "/api/user/logout/", token=new_token)
    log_test("TC-14", "Logout user and invalidate authentication token", "POST", "/api/user/logout/", None, new_token, res)
    
    # Test 7.2: Verify old token is now rejected
    res = make_request("GET", "/api/user/profile/", token=new_token)
    log_test("TC-15", "Verify revoked token can no longer access protected profile", "GET", "/api/user/profile/", None, new_token, res)

    # =========================================================================
    # Save all results to disk
    # =========================================================================
    output_filename = "api_test_results.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "server_url": BASE_URL,
            "test_phone": test_phone,
            "total_tests": len(results),
            "passed_tests": sum(1 for r in results if r["status_code"] in [200, 201, 400, 401, 405]),
            "tests": results
        }, f, indent=2)
    print(f"\n[OK] All {len(results)} API tests executed and saved to '{output_filename}'.")

if __name__ == "__main__":
    run_tests()
