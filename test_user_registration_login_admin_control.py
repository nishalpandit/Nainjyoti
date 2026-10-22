import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from nainjyoti.models import UserProfile, OTPRecord

client = Client()

print("==========================================================")
print(" TEST SUITE: USER REGISTRATION, LOGIN & ADMIN DASHBOARD CONTROL")
print("==========================================================")

# Clean up test phone if exists
test_phone = "9812345678"
UserProfile.objects.filter(phone=test_phone).delete()
User.objects.filter(username__startswith=f"usr_{test_phone}").delete()
OTPRecord.objects.filter(phone=test_phone).delete()

# 1. Test Send OTP for new phone
res1 = client.post('/api/user/send-otp/', data=json.dumps({"phone": test_phone}), content_type='application/json')
assert res1.status_code == 200, f"Failed res1: {res1.content}"
data1 = res1.json()
assert data1['success'] is True
assert data1['is_registered'] is False
assert data1['action'] == 'REGISTER'
otp_code = data1['otp_debug']
print(f" [PASS] 1. Send OTP for new phone: received OTP {otp_code}")

# 2. Test Verify OTP before registration (prompts user to register)
res2 = client.post('/api/user/verify-otp-login/', data=json.dumps({"phone": test_phone, "otp": otp_code}), content_type='application/json')
assert res2.status_code == 200, f"Failed res2: {res2.content}"
data2 = res2.json()
assert data2['success'] is True
assert data2['is_registered'] is False
assert data2['otp_verified'] is True
print(" [PASS] 2. Verify OTP for new phone: verified successfully, prompt registration")

# 3. Test User Registration with password
reg_payload = {
    "first_name": "Dev",
    "last_name": "Sharma",
    "phone": test_phone,
    "email": "dev.sharma@example.com",
    "password": "Password@2026",
    "gender": "Male",
    "dob": "1995-08-15"
}
res3 = client.post('/api/user/register/', data=json.dumps(reg_payload), content_type='application/json')
assert res3.status_code == 201, f"Failed res3: {res3.content}"
data3 = res3.json()
assert data3['success'] is True
assert 'token' in data3
token = data3['token']
user_id = data3['user']['id']
print(f" [PASS] 3. User Registration: created User ID {user_id} with Bearer Token {token[:12]}...")

# 4. Test User Auth Status
res4 = client.get('/api/user/status/', HTTP_AUTHORIZATION=f"Bearer {token}")
assert res4.status_code == 200, f"Failed res4: {res4.content}"
data4 = res4.json()
assert data4['authenticated'] is True
assert data4['user']['phone'] == test_phone
print(" [PASS] 4. User Status API: authenticated successfully")

# 5. Test Password Login with Phone
res5 = client.post('/api/user/login/', data=json.dumps({"identifier": test_phone, "password": "Password@2026"}), content_type='application/json')
assert res5.status_code == 200, f"Failed res5: {res5.content}"
data5 = res5.json()
assert data5['success'] is True
token5 = data5['token']
print(" [PASS] 5. Password Login via Phone: authenticated successfully")

# 6. Test Password Login with Email
res6 = client.post('/api/user/login/', data=json.dumps({"identifier": "dev.sharma@example.com", "password": "Password@2026"}), content_type='application/json')
assert res6.status_code == 200, f"Failed res6: {res6.content}"
print(" [PASS] 6. Password Login via Email: authenticated successfully")

# 7. Test OTP Login for already registered phone
res7_otp = client.post('/api/user/send-otp/', data=json.dumps({"phone": test_phone}), content_type='application/json')
assert res7_otp.status_code == 200
data7_otp = res7_otp.json()
assert data7_otp['is_registered'] is True
assert data7_otp['action'] == 'LOGIN'
res7_login = client.post('/api/user/verify-otp-login/', data=json.dumps({"phone": test_phone, "otp": data7_otp['otp_debug']}), content_type='application/json')
assert res7_login.status_code == 200
data7_login = res7_login.json()
assert data7_login['is_registered'] is True
print(" [PASS] 7. OTP Sign-in for registered user: authenticated successfully")

# 8. Test Admin Dashboard Controls: Toggle Status to Block/Deactivate
admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
client.force_login(admin_user)

res8_toggle = client.post(f'/admin-dashboard/customers/{user_id}/toggle-status/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
assert res8_toggle.status_code == 200, f"Failed res8_toggle: {res8_toggle.content}"
data8_toggle = res8_toggle.json()
assert data8_toggle['is_active'] is False
print(f" [PASS] 8. Admin Control: Blocked customer {user_id}")

# 9. Verify Deactivated User is strictly BLOCKED across all APIs
res9_status = client.get('/api/user/status/', HTTP_AUTHORIZATION=f"Bearer {token}")
assert res9_status.status_code == 403, f"Expected 403, got {res9_status.status_code}"
assert "deactivated" in res9_status.json()['message'].lower()

res9_login = client.post('/api/user/login/', data=json.dumps({"identifier": test_phone, "password": "Password@2026"}), content_type='application/json')
assert res9_login.status_code == 403
assert "deactivated" in res9_login.json()['message'].lower()

res9_otp = client.post('/api/user/send-otp/', data=json.dumps({"phone": test_phone}), content_type='application/json')
assert res9_otp.status_code == 403
assert "deactivated" in res9_otp.json()['message'].lower()
print(" [PASS] 9. Blocked Account Enforcement: 403 Forbidden verified on status, password login, and OTP")

# 10. Admin Unblocks the user
res10_toggle = client.post(f'/admin-dashboard/customers/{user_id}/toggle-status/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
assert res10_toggle.status_code == 200
assert res10_toggle.json()['is_active'] is True
print(f" [PASS] 10. Admin Control: Unblocked/Activated customer {user_id}")

# 11. User can log in again after unblock
res11_login = client.post('/api/user/login/', data=json.dumps({"identifier": test_phone, "password": "Password@2026"}), content_type='application/json')
assert res11_login.status_code == 200
active_token = res11_login.json()['token']
print(" [PASS] 11. Unblocked User Login: successfully authenticated again")

# 12. Test Admin Customer Dossier Detail View
res12_detail = client.get(f'/admin-dashboard/customers/{user_id}/detail/')
assert res12_detail.status_code == 200
cust_dossier = res12_detail.json()['customer']
assert cust_dossier['phone'] == test_phone
assert cust_dossier['first_name'] == "Dev"
assert cust_dossier['is_active'] is True
print(f" [PASS] 12. Admin Customer Dossier: fetched full profile details for {cust_dossier['full_name']}")

# 13. Test User Logout
res13_logout = client.post('/api/user/logout/', HTTP_AUTHORIZATION=f"Bearer {active_token}")
assert res13_logout.status_code == 200
assert res13_logout.json()['success'] is True
print(" [PASS] 13. User Logout: session terminated and token rotated")

print("\n==========================================================")
print(" ALL 13 TEST CASES PASSED WITH 100% SUCCESS!")
print("==========================================================")
