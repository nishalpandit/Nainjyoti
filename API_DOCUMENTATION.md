API for Send OTP (Customer)
url: http://192.168.1.52:8000/api/user/send-otp/
method: POST

params:
phone: 9876543211

response:
{
  "success": true,
  "message": "OTP sent for login to 9876543211",
  "phone": "9876543211",
  "is_registered": true,
  "action": "LOGIN",
  "otp_debug": "598906",
  "expires_in_minutes": 10
}

API for Verify OTP Login (Customer)
url: http://192.168.1.52:8000/api/user/verify-otp-login/
method: POST

params:
phone: 9876543211
otp: 598906

response:
{
  "success": true,
  "message": "Login successful",
  "is_registered": true,
  "token": "b1e4ac004e78dc09cf5d6d88e0002161cd087e547519fae28de0da1f59511b0e",
  "user": {
    "id": 3,
    "first_name": "Ananya",
    "last_name": "Iyer",
    "full_name": "Ananya Iyer",
    "phone": "9876543211",
    "email": "ananya.updated@example.com",
    "dob": "1999-04-12",
    "gender": "Female",
    "profile_photo": "/media/user_profiles/photos/ananya_profile.png",
    "created_at": "2026-10-10T10:47:11.729459+00:00"
  }
}

API for Customer Registration
url: http://192.168.1.52:8000/api/user/register/
method: POST

params:
first_name: Ananya
last_name: Iyer
phone: 9876543211
email: ananya.iyer@example.com
dob: 1999-04-12
gender: Female
profile_photo: ananya_profile.png

response:
{
  "success": true,
  "message": "User registered successfully",
  "token": "d3e59fe660caa5dd301ee1edeabe420e2f6e0037a67682ce6c46e8f9fd13a721",
  "user": {
    "id": 3,
    "first_name": "Ananya",
    "last_name": "Iyer",
    "full_name": "Ananya Iyer",
    "phone": "9876543211",
    "email": "ananya.iyer@example.com",
    "dob": "1999-04-12",
    "gender": "Female",
    "profile_photo": "/media/user_profiles/photos/ananya_profile.png",
    "created_at": "2026-10-10T10:47:11.729459+00:00"
  }
}

API for Get Customer Profile
url: http://192.168.1.52:8000/api/user/profile/
method: GET

headers:
Authorization: Bearer b1e4ac004e78dc09cf5d6d88e0002161cd087e547519fae28de0da1f59511b0e

response:
{
  "success": true,
  "user": {
    "id": 3,
    "first_name": "Ananya",
    "last_name": "Iyer",
    "full_name": "Ananya Iyer",
    "phone": "9876543211",
    "email": "ananya.updated@example.com",
    "dob": "1999-04-12",
    "gender": "Female",
    "profile_photo": "/media/user_profiles/photos/ananya_profile.png",
    "created_at": "2026-10-10T10:47:11.729459+00:00"
  }
}

API for Update Customer Profile
url: http://192.168.1.52:8000/api/user/profile/
method: POST

headers:
Authorization: Bearer b1e4ac004e78dc09cf5d6d88e0002161cd087e547519fae28de0da1f59511b0e

params:
first_name: Ananya
last_name: Iyer
email: ananya.updated@example.com
dob: 1999-04-12
gender: Female

response:
{
  "success": true,
  "message": "Profile updated successfully",
  "user": {
    "id": 3,
    "first_name": "Ananya",
    "last_name": "Iyer",
    "full_name": "Ananya Iyer",
    "phone": "9876543211",
    "email": "ananya.updated@example.com",
    "dob": "1999-04-12",
    "gender": "Female",
    "profile_photo": "/media/user_profiles/photos/ananya_profile.png",
    "created_at": "2026-10-10T10:47:11.729459+00:00"
  }
}

API for Customer Logout
url: http://192.168.1.52:8000/api/user/logout/
method: POST

headers:
Authorization: Bearer b1e4ac004e78dc09cf5d6d88e0002161cd087e547519fae28de0da1f59511b0e

response:
{
  "success": true,
  "message": "User successfully logged out"
}
