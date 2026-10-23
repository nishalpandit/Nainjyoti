import os
import sys
import django
import io
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from nainjyoti.models import UserProfile, Order

def create_dummy_image(name="test_avatar.png", color="blue"):
    file_obj = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=color)
    img.save(file_obj, format="PNG")
    file_obj.seek(0)
    return SimpleUploadedFile(name, file_obj.read(), content_type="image/png")

def run_tests():
    print("=" * 60)
    print("RUNNING STEP 2: USER PROFILE, PHOTO UPLOAD & ADMIN CONTROL TESTS")
    print("=" * 60)

    client = Client()

    # 1. Setup Test Users
    phone1 = "9899112233"
    phone2 = "9899445566"
    test_emails = ["aarav.kumar@example.com", "pooja.sharma@example.com", "aarav.mehta@example.com", "aarav.adminedit@example.com"]

    # Cleanup existing
    UserProfile.objects.filter(phone__in=[phone1, phone2]).delete()
    UserProfile.objects.filter(email__in=test_emails).delete()
    User.objects.filter(username__in=[f"usr_{phone1}", f"usr_{phone2}"]).delete()
    User.objects.filter(email__in=test_emails).delete()

    # User 1
    u1 = User.objects.create_user(username=f"usr_{phone1}", first_name="Aarav", last_name="Kumar", email="aarav.kumar@example.com")
    u1.set_password("Pass@1234")
    u1.save()
    p1 = UserProfile.objects.create(
        user=u1,
        first_name="Aarav",
        last_name="Kumar",
        phone=phone1,
        email="aarav.kumar@example.com",
        gender="Male",
        is_active=True
    )
    token1 = p1.auth_token

    # User 2
    u2 = User.objects.create_user(username=f"usr_{phone2}", first_name="Pooja", last_name="Sharma", email="pooja.sharma@example.com")
    u2.set_password("Pass@1234")
    u2.save()
    p2 = UserProfile.objects.create(
        user=u2,
        first_name="Pooja",
        last_name="Sharma",
        phone=phone2,
        email="pooja.sharma@example.com",
        gender="Female",
        is_active=True
    )

    print("[PASS] Test fixtures created successfully")

    # Test 1: GET Profile with No Token (401 Expected)
    res = client.get('/api/user/profile/')
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    print("[PASS] Test 1: GET /api/user/profile/ without token returns 401")

    # Test 2: GET Profile with Valid Bearer Token (200 Expected)
    res = client.get('/api/user/profile/', HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data['success'] is True
    assert data['user']['phone'] == phone1
    assert data['user']['full_name'] == "Aarav Kumar"
    assert 'total_orders' in data['user']
    assert 'total_spent' in data['user']
    print(f"[PASS] Test 2: GET /api/user/profile/ returns profile for {data['user']['full_name']}")

    # Test 3: POST /api/user/profile/update/ (Update Personal Details)
    update_payload = {
        'first_name': 'Aarav Dev',
        'last_name': 'Mehta',
        'gender': 'Male',
        'dob': '1996-05-20',
        'email': 'aarav.mehta@example.com'
    }
    res = client.post('/api/user/profile/update/', update_payload, HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.content}"
    data = res.json()
    assert data['success'] is True
    assert data['user']['full_name'] == "Aarav Dev Mehta"
    assert data['user']['email'] == "aarav.mehta@example.com"
    assert data['user']['dob'] == "1996-05-20"
    p1.refresh_from_db()
    assert p1.first_name == "Aarav Dev"
    assert p1.last_name == "Mehta"
    assert p1.email == "aarav.mehta@example.com"
    print("[PASS] Test 3: POST /api/user/profile/update/ successfully updated names, email, dob")

    # Test 4: Email Conflict on Profile Update (400 Expected)
    conflict_payload = {
        'email': 'pooja.sharma@example.com' # Already used by User 2
    }
    res = client.post('/api/user/profile/update/', conflict_payload, HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 400, f"Expected 400 for duplicate email, got {res.status_code}"
    assert "already in use" in res.json()['message']
    print("[PASS] Test 4: Email uniqueness enforcement validated on profile update")

    # Test 5: POST /api/user/profile/photo/ (Upload Binary Profile Photo)
    img_file = create_dummy_image("aarav_pic.png", "green")
    res = client.post('/api/user/profile/photo/', {'profile_photo': img_file}, HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.content}"
    data = res.json()
    assert data['success'] is True
    assert data['profile_photo'] is not None
    assert "/media/user_profiles/photos/" in data['profile_photo']
    p1.refresh_from_db()
    assert p1.profile_photo is not None
    print(f"[PASS] Test 5: Profile photo uploaded successfully: {data['profile_photo']}")

    # Test 6: POST /api/user/profile/photo/ (Remove Photo)
    res = client.post('/api/user/profile/photo/', {'remove_photo': 'true'}, HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.content}"
    data = res.json()
    assert data['success'] is True
    assert data['profile_photo'] is None
    p1.refresh_from_db()
    assert not bool(p1.profile_photo)
    print("[PASS] Test 6: Profile photo successfully removed")

    # Test 7: Admin Control: Edit Customer Profile via POST /admin-dashboard/customers/<id>/edit/
    admin_edit_payload = {
        'first_name': 'Aarav AdminEdit',
        'last_name': 'Mehta Senior',
        'gender': 'Male',
        'phone': '9899112233',
        'email': 'aarav.adminedit@example.com'
    }
    res = client.post(f'/admin-dashboard/customers/{p1.id}/edit/', admin_edit_payload, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.content}"
    data = res.json()
    assert data['success'] is True
    assert data['customer']['full_name'] == "Aarav AdminEdit Mehta Senior"
    p1.refresh_from_db()
    assert p1.full_name == "Aarav AdminEdit Mehta Senior"
    print("[PASS] Test 7: Admin customer profile edit endpoint verified")

    # Test 8: Admin Control: Block Customer Account
    res = client.post(f'/admin-dashboard/customers/{p1.id}/toggle-status/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert res.status_code == 200
    p1.refresh_from_db()
    assert p1.is_active is False
    print("[PASS] Test 8: Admin successfully toggled status to BLOCKED")

    # Test 9: Deactivated User Calling Profile Endpoint (403 Expected)
    res = client.get('/api/user/profile/', HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"
    assert "deactivated by administrator" in res.json()['message']
    print("[PASS] Test 9: Blocked customer receiving 403 on GET /api/user/profile/")

    # Test 10: Deactivated User Calling Update Endpoint (403 Expected)
    res = client.post('/api/user/profile/update/', {'first_name': 'Hacker'}, HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"
    print("[PASS] Test 10: Blocked customer receiving 403 on POST /api/user/profile/update/")

    # Test 11: Deactivated User Calling Photo Endpoint (403 Expected)
    res = client.post('/api/user/profile/photo/', {'profile_photo': create_dummy_image()}, HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}"
    print("[PASS] Test 11: Blocked customer receiving 403 on POST /api/user/profile/photo/")

    # Test 12: Admin Unblocks Customer -> Re-enables Access
    res = client.post(f'/admin-dashboard/customers/{p1.id}/toggle-status/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert res.status_code == 200
    p1.refresh_from_db()
    assert p1.is_active is True
    res = client.get('/api/user/profile/', HTTP_AUTHORIZATION=f"Bearer {token1}")
    assert res.status_code == 200
    print("[PASS] Test 12: Admin unblocked customer, API access immediately restored")

    # Cleanup
    p1.delete()
    u1.delete()
    p2.delete()
    u2.delete()

    print("\n=======================================================")
    print(" ALL 12 TESTS PASSED PERFECTLY!")
    print("=======================================================\n")

if __name__ == '__main__':
    run_tests()
