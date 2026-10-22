API for Requesting OTP for User Login or Registration
url: http://192.168.1.52:8000/api/user/send-otp/
method: POST

headers:
Content-Type: multipart/form-data

params:
phone: 9812345678

response:
```json
{
  "success": true,
  "message": "Phone not registered. OTP sent for registration to 9812345678",
  "phone": "9812345678",
  "is_registered": false,
  "action": "REGISTER",
  "otp_debug": "802881",
  "expires_in_minutes": 10
}
```

response (for existing registered user):
```json
{
  "success": true,
  "message": "OTP sent for login to 9812345678",
  "phone": "9812345678",
  "is_registered": true,
  "action": "LOGIN",
  "otp_debug": "942730",
  "expires_in_minutes": 10
}
```

response (if account was deactivated / blocked by admin):
```json
{
  "success": false,
  "message": "Your account has been deactivated by administrator. Please contact support."
}
```

API for Verifying OTP and Sign In
url: http://192.168.1.52:8000/api/user/verify-otp-login/
method: POST

headers:
Content-Type: multipart/form-data

params:
phone: 9812345678
otp: 942730

response (successful login for registered user):
```json
{
  "success": true,
  "message": "Login successful",
  "is_registered": true,
  "token": "bcc76b37b494632822a16cb7a3fa7a49942a17070f80da7cbceee402b8514197",
  "user": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Sharma",
    "full_name": "Dev Sharma",
    "phone": "9812345678",
    "email": "dev.sharma@example.com",
    "dob": "1995-08-15",
    "gender": "Male",
    "profile_photo": null,
    "is_active": true,
    "created_at": "2026-10-22T12:25:46.398042+00:00"
  }
}
```

response (for verified new phone, ready to complete registration):
```json
{
  "success": true,
  "message": "Phone number verified. Please complete user registration.",
  "is_registered": false,
  "phone": "9812345678",
  "otp_verified": true
}
```

response (if account was deactivated / blocked by admin):
```json
{
  "success": false,
  "message": "Your account has been deactivated by administrator. Please contact support."
}
```

API for User Registration
url: http://192.168.1.52:8000/api/user/register/
method: POST

headers:
Content-Type: multipart/form-data

params:
first_name: Dev
last_name: Sharma
phone: 9812345678
email: dev.sharma@example.com (optional)
password: Password@2026 (optional, enables direct password login)
gender: Male (choices: Male, Female, Other, Prefer not to say)
dob: 1995-08-15 (optional, YYYY-MM-DD)
profile_photo: [Upload binary image file, e.g. avatar.jpg / png] (optional)

response:
```json
{
  "success": true,
  "message": "User registered successfully",
  "token": "bcc76b37b494632822a16cb7a3fa7a49942a17070f80da7cbceee402b8514197",
  "user": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Sharma",
    "full_name": "Dev Sharma",
    "phone": "9812345678",
    "email": "dev.sharma@example.com",
    "dob": "1995-08-15",
    "gender": "Male",
    "profile_photo": "/media/user_profiles/photos/avatar.jpg",
    "is_active": true,
    "created_at": "2026-10-22T12:25:46.398042+00:00"
  }
}
```

API for Direct Password Login (Phone or Email)
url: http://192.168.1.52:8000/api/user/login/
method: POST

headers:
Content-Type: multipart/form-data

params:
identifier: 9812345678 (or user email address, e.g. dev.sharma@example.com)
password: Password@2026

response:
```json
{
  "success": true,
  "message": "Login successful",
  "token": "bcc76b37b494632822a16cb7a3fa7a49942a17070f80da7cbceee402b8514197",
  "user": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Sharma",
    "full_name": "Dev Sharma",
    "phone": "9812345678",
    "email": "dev.sharma@example.com",
    "dob": "1995-08-15",
    "gender": "Male",
    "profile_photo": null,
    "is_active": true,
    "created_at": "2026-10-22T12:25:46.398042+00:00"
  }
}
```

response (if account was deactivated / blocked by admin):
```json
{
  "success": false,
  "message": "Your account has been deactivated by administrator. Please contact support."
}
```

API for Checking User Authentication Status & Admin Access Health
url: http://192.168.1.52:8000/api/user/status/
method: GET

headers:
Authorization: Bearer <user_token> (required)

params:
none

response (if active and authenticated):
```json
{
  "success": true,
  "authenticated": true,
  "is_active": true,
  "user": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Sharma",
    "full_name": "Dev Sharma",
    "phone": "9812345678",
    "email": "dev.sharma@example.com",
    "dob": "1995-08-15",
    "gender": "Male",
    "profile_photo": null,
    "is_active": true,
    "created_at": "2026-10-22T12:25:46.398042+00:00"
  }
}
```

response (if blocked / deactivated by administrator):
```json
{
  "success": false,
  "authenticated": false,
  "is_active": false,
  "message": "Your account has been deactivated by administrator. Please contact support."
}
```

API for User Logout
url: http://192.168.1.52:8000/api/user/logout/
method: POST

headers:
Authorization: Bearer <user_token> (required)
Content-Type: multipart/form-data

params:
none

response:
```json
{
  "success": true,
  "message": "User successfully logged out"
}
```

API for Admin Dashboard: Toggle Customer Account Status (Activate or Block)
url: http://192.168.1.52:8000/admin-dashboard/customers/<customer_id>/toggle-status/
method: POST

headers:
X-Requested-With: XMLHttpRequest (or standard browser form submission)

params:
none

response:
```json
{
  "success": true,
  "message": "Customer 'Dev Sharma' (9812345678) has been DEACTIVATED / BLOCKED.",
  "customer_id": 7,
  "is_active": false,
  "status_label": "Blocked"
}
```

API for Admin Dashboard: Fetch Customer Full Dossier & Order History
url: http://192.168.1.52:8000/admin-dashboard/customers/<customer_id>/detail/
method: GET

headers:
none

params:
none

response:
```json
{
  "success": true,
  "customer": {
    "id": 7,
    "customer_code": "CUS-48207",
    "full_name": "Dev Sharma",
    "first_name": "Dev",
    "last_name": "Sharma",
    "phone": "9812345678",
    "email": "dev.sharma@example.com",
    "gender": "Male",
    "dob": "15 Aug 1995",
    "photo_url": null,
    "is_active": true,
    "registered_at": "22 Oct 2026 17:55",
    "total_orders": 3,
    "lifetime_value": "₹4,999",
    "recent_orders": [
      {
        "order_number": "ORD-20261017-4360",
        "total_amount": "₹4,999",
        "status": "DELIVERED",
        "status_display": "Delivered",
        "created_at": "17 Oct 2026 10:54"
      }
    ]
  }
}
```
