# Nainjyoti User & Customer API Documentation

> **Bearer Token Authentication Policy**:
> - **Bearer Token Expiry**: **Never Expires (Permanent)**
> - The Bearer token issued upon sign-in or registration (`Authorization: Bearer <token>`) has **NO expiry time** and **never expires automatically**.
> - The token remains active indefinitely until explicit logout (`/api/user/logout/`) or optional manual rotation (`/api/user/refresh-token/`).

---

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
  "otp_debug": "802881"
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
  "otp_debug": "942730"
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
    "profile_photo": "/media/user_profiles/photos/default_avatar.png",
    "is_active": true,
    "created_at": "2026-10-22T12:25:46.398042+00:00"
  }
}
```

API for Refreshing User Token (Optional Manual Rotation)
*Note: Bearer tokens never expire automatically. This endpoint is strictly optional if a client application wishes to manually rotate an active Bearer token.*
url: http://192.168.1.52:8000/api/user/refresh-token/
method: POST

headers:
Authorization: Bearer <current_token>

params (optional fallback if not sending header):
{
  "token": "bcc76b37b494632822a16cb7a3fa7a49942a17070f80da7cbceee402b8514197"
}

response:
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "auth_token": "f920d6a0028713bb93c20054ec5a7a49942a17070f80da7cbceee402b8514197",
  "token": "f920d6a0028713bb93c20054ec5a7a49942a17070f80da7cbceee402b8514197",
  "user": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Sharma",
    "full_name": "Dev Sharma",
    "phone": "9812345678",
    "email": "dev.sharma@example.com"
  }
}
```

response (if token is invalid or missing):
```json
{
  "success": false,
  "message": "Invalid or missing token. Please provide a valid Bearer token."
}
```

API for User Logout
url: http://192.168.1.52:8000/api/user/logout/
method: POST

headers:
Authorization: Bearer <current_token>

response:
```json
{
  "success": true,
  "message": "User successfully logged out"
}
```

---

API for Update Customer Profile
url: http://192.168.1.52:8000/api/user/profile/update/
method: POST (or PUT)

headers:
Authorization: Bearer <user_token>
Content-Type: multipart/form-data (when attaching photo file) or application/json

params (form-data or json):
first_name: Dev
last_name: Sharma
email: dev.sharma@example.com
dob: 1995-08-15
gender: Male
profile_photo: [Attach image file, or base64 data, or filename]

response:
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "user": {
    "id": 9,
    "first_name": "Dev",
    "last_name": "Sharma",
    "full_name": "Dev Sharma",
    "phone": "1234567890",
    "email": "dev.sharma@example.com",
    "dob": "1995-08-15",
    "gender": "Male",
    "profile_photo": "/media/user_profiles/photos/user_9_ab12cd34.png",
    "is_active": true,
    "created_at": "2026-10-23T05:35:40.995425+00:00",
    "total_orders": 0,
    "total_spent": 0.0
  }
}
```

---

API for Dedicated Profile Photo Upload
url: http://192.168.1.52:8000/api/user/profile/photo/
method: POST

headers:
Authorization: Bearer <user_token>
Content-Type: multipart/form-data

params:
profile_photo: [binary image file]

response:
```json
{
  "success": true,
  "message": "Profile photo uploaded successfully",
  "profile_photo": "/media/user_profiles/photos/user_9_ab12cd34.png",
  "user": {
    "id": 9,
    "first_name": "Dev",
    "last_name": "Sharma",
    "full_name": "Dev Sharma",
    "profile_photo": "/media/user_profiles/photos/user_9_ab12cd34.png"
  }
}
```

---

API for Creating a Saved Address
url: http://192.168.1.52:8000/api/user/address/create/
method: POST

headers:
Authorization: Bearer USER_TOKEN
Content-Type: multipart/form-data

params:
address_type: Home
full_name: Ananya Iyer
phone: 9876543211
address_line_1: 12, MG Road
address_line_2: Apartment 4B
landmark: Near Metro Station
city: Bengaluru
state: Karnataka
pincode: 560001
country: India
is_default: true

response:
```json
{
  "success": true,
  "message": "Address added successfully",
  "address": {
    "id": 1,
    "address_type": "Home",
    "full_name": "Ananya Iyer",
    "phone": "9876543211",
    "address_line_1": "12, MG Road",
    "address_line_2": "Apartment 4B",
    "landmark": "Near Metro Station",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
    "country": "India",
    "is_default": true,
    "created_at": "2026-10-23T06:13:59.358870+00:00",
    "updated_at": "2026-10-23T06:13:59.358899+00:00"
  }
}
```

API for Listing Saved Addresses
url: http://192.168.1.52:8000/api/user/address/list/
method: GET

headers:
Authorization: Bearer USER_TOKEN

params:
No body params

response:
```json
{
  "success": true,
  "message": "Addresses fetched successfully",
  "count": 1,
  "default_address_id": 1,
  "addresses": [
    {
      "id": 1,
      "address_type": "Home",
      "full_name": "Ananya Iyer",
      "phone": "9876543211",
      "address_line_1": "12, MG Road",
      "address_line_2": "Apartment 4B",
      "landmark": "Near Metro Station",
      "city": "Bengaluru",
      "state": "Karnataka",
      "pincode": "560001",
      "country": "India",
      "is_default": true,
      "created_at": "2026-10-23T06:13:59.358870+00:00",
      "updated_at": "2026-10-23T06:13:59.358899+00:00"
    }
  ]
}
```

API for Getting One Saved Address
url: http://192.168.1.52:8000/api/user/address/detail/1/
method: GET

headers:
Authorization: Bearer USER_TOKEN

params:
No body params

response:
```json
{
  "success": true,
  "message": "Address fetched successfully",
  "address": {
    "id": 1,
    "address_type": "Home",
    "full_name": "Ananya Iyer",
    "phone": "9876543211",
    "address_line_1": "12, MG Road",
    "address_line_2": "Apartment 4B",
    "landmark": "Near Metro Station",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
    "country": "India",
    "is_default": true,
    "created_at": "2026-10-23T06:13:59.358870+00:00",
    "updated_at": "2026-10-23T06:13:59.358899+00:00"
  }
}
```

API for Updating a Saved Address
url: http://192.168.1.52:8000/api/user/address/update/1/
method: POST

headers:
Authorization: Bearer USER_TOKEN
Content-Type: multipart/form-data

params (send one or more fields):
address_type: Work
address_line_1: 44, Residency Road
landmark: Opposite City Library
city: Bengaluru
state: Karnataka
pincode: 560025

response:
```json
{
  "success": true,
  "message": "Address updated successfully",
  "address": {
    "id": 1,
    "address_type": "Work",
    "full_name": "Ananya Iyer",
    "phone": "9876543211",
    "address_line_1": "44, Residency Road",
    "address_line_2": "Apartment 4B",
    "landmark": "Opposite City Library",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560025",
    "country": "India",
    "is_default": true,
    "created_at": "2026-10-23T00:00:00+00:00",
    "updated_at": "2026-10-23T00:00:00+00:00"
  }
}
```

API for Setting the Default Address
url: http://192.168.1.52:8000/api/user/address/set-default/1/
method: POST

headers:
Authorization: Bearer USER_TOKEN

params:
No body params

response:
```json
{
  "success": true,
  "message": "Default address updated successfully",
  "address": {
    "id": 1,
    "is_default": true
  }
}
```

API for Deleting a Saved Address
url: http://192.168.1.52:8000/api/user/address/delete/1/
method: DELETE

headers:
Authorization: Bearer USER_TOKEN

params:
No body params

response:
```json
{
  "success": true,
  "message": "Address deleted successfully",
  "deleted_address_id": 1
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

API for Fetching User Profile
url: http://192.168.1.52:8000/api/user/profile/
method: GET

headers:
Authorization: Bearer <user_token>

params:
none

response (active authenticated user):
```json
{
  "success": true,
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
    "created_at": "2026-10-22T12:25:46.398042+00:00",
    "total_orders": 3,
    "total_spent": 4999.0
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

API for Updating User Profile Details
url: http://192.168.1.52:8000/api/user/profile/update/
method: POST (or PUT)

headers:
Authorization: Bearer <user_token>
Content-Type: multipart/form-data

params:
first_name: Dev (optional)
last_name: Verma (optional)
email: dev.verma@example.com (optional)
gender: Male (optional, choices: Male, Female, Other, Prefer not to say)
dob: 1995-08-15 (optional, YYYY-MM-DD or DD/MM/YYYY)
profile_photo: [Upload binary image file, e.g. avatar.jpg / png] (optional)
remove_photo: true (optional, set true to remove profile photo)

response:
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "user": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Verma",
    "full_name": "Dev Verma",
    "phone": "9812345678",
    "email": "dev.verma@example.com",
    "dob": "1995-08-15",
    "gender": "Male",
    "profile_photo": "/media/user_profiles/photos/avatar.jpg",
    "is_active": true,
    "created_at": "2026-10-22T12:25:46.398042+00:00",
    "total_orders": 3,
    "total_spent": 4999.0
  }
}
```

response (if email is already used by another account):
```json
{
  "success": false,
  "message": "This email address is already in use by another account."
}
```

API for Uploading or Updating User Profile Photo
url: http://192.168.1.52:8000/api/user/profile/photo/
method: POST

headers:
Authorization: Bearer <user_token>
Content-Type: multipart/form-data

params:
profile_photo: [Upload binary image file, e.g. photo.jpg / png]

response (photo uploaded):
```json
{
  "success": true,
  "message": "Profile photo uploaded successfully",
  "profile_photo": "/media/user_profiles/photos/photo.jpg",
  "user": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Verma",
    "full_name": "Dev Verma",
    "phone": "9812345678",
    "email": "dev.verma@example.com",
    "dob": "1995-08-15",
    "gender": "Male",
    "profile_photo": "/media/user_profiles/photos/photo.jpg",
    "is_active": true,
    "created_at": "2026-10-22T12:25:46.398042+00:00"
  }
}
```

params (to remove profile photo):
remove_photo: true

response (photo removed):
```json
{
  "success": true,
  "message": "Profile photo removed successfully",
  "profile_photo": null,
  "user": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Verma",
    "full_name": "Dev Verma",
    "phone": "9812345678",
    "email": "dev.verma@example.com",
    "dob": "1995-08-15",
    "gender": "Male",
    "profile_photo": null,
    "is_active": true,
    "created_at": "2026-10-22T12:25:46.398042+00:00"
  }
}
```

API for Admin Dashboard: Edit Customer Profile Details & Status
url: http://192.168.1.52:8000/admin-dashboard/customers/<customer_id>/edit/
method: POST

headers:
Content-Type: multipart/form-data
X-Requested-With: XMLHttpRequest (optional for JSON response)

params:
first_name: Dev (optional)
last_name: Verma (optional)
phone: 9812345678 (optional)
email: dev.verma@example.com (optional)
gender: Male (optional, choices: Male, Female, Other, Prefer not to say)
dob: 1995-08-15 (optional, YYYY-MM-DD)
profile_photo: [Upload binary image file, e.g. photo.jpg / png] (optional)
remove_photo: true (optional)
is_active: true (optional, boolean: true / false)

response:
```json
{
  "success": true,
  "message": "Customer 'Dev Verma' updated successfully.",
  "customer": {
    "id": 7,
    "first_name": "Dev",
    "last_name": "Verma",
    "full_name": "Dev Verma",
    "phone": "9812345678",
    "email": "dev.verma@example.com",
    "gender": "Male",
    "dob": "1995-08-15",
    "photo_url": "/media/user_profiles/photos/photo.jpg",
    "is_active": true
  }
}
```



API for Listing Active Product Categories
url: http://192.168.1.52:8000/api/user/categories/
method: GET

headers:
none (public endpoint)

params:
q: Electronics (optional keyword search for category name)

response:
```json
{
  "success": true,
  "message": "Categories fetched successfully",
  "count": 2,
  "categories": [
    {
      "id": 1,
      "name": "Electronics & Gadgets",
      "description": "Smartphones, audio, and accessories",
      "image_url": "/media/categories/images/electronics.jpg",
      "status": "ACTIVE",
      "products_count": 24,
      "created_at": "2026-10-17T04:47:00+00:00",
      "updated_at": "2026-10-23T06:40:00+00:00"
    },
    {
      "id": 2,
      "name": "Clothing & Apparel",
      "description": "Men's and women's fashion wear",
      "image_url": "/media/categories/images/fashion.jpg",
      "status": "ACTIVE",
      "products_count": 18,
      "created_at": "2026-10-17T04:48:00+00:00",
      "updated_at": "2026-10-23T06:40:00+00:00"
    }
  ]
}
```

API for Getting Single Category Details
url: http://192.168.1.52:8000/api/user/categories/<category_id>/
method: GET

headers:
none (public endpoint)

params:
none

response (active category):
```json
{
  "success": true,
  "message": "Category fetched successfully",
  "category": {
    "id": 1,
    "name": "Electronics & Gadgets",
    "description": "Smartphones, audio, and accessories",
    "image_url": "/media/categories/images/electronics.jpg",
    "status": "ACTIVE",
    "products_count": 24,
    "created_at": "2026-10-17T04:47:00+00:00",
    "updated_at": "2026-10-23T06:40:00+00:00"
  }
}
```

response (if category is inactive or does not exist):
```json
{
  "success": false,
  "message": "Category with ID '1' was not found or is inactive."
}
```

API for Fetching Products Under a Specific Category
url: http://192.168.1.52:8000/api/user/categories/<category_id>/products/
method: GET

headers:
none (public endpoint)

params (query parameters):
q: headphones (optional keyword search within this category)
min_price: 500 (optional minimum price)
max_price: 3000 (optional maximum price)
in_stock: true (optional, true/1 to only show in-stock products)
sort: price_low_to_high (options: price_low_to_high, price_high_to_low, newest; default: newest)
page: 1 (optional, default: 1)
limit: 20 (optional, default: 20, max: 100)

response:
```json
{
  "success": true,
  "category": {
    "id": 1,
    "name": "Electronics & Gadgets",
    "description": "Smartphones, audio, and accessories",
    "image_url": "/media/categories/images/electronics.jpg",
    "total_products": 24
  },
  "total_products": 24,
  "page": 1,
  "total_pages": 2,
  "has_next": true,
  "products": [
    {
      "id": 10,
      "name": "Wireless Noise Cancelling Headphones",
      "sku": "PRD-2039",
      "price": 2999.0,
      "discount_price": 2499.0,
      "image_url": "/media/products/headphones.jpg",
      "category_id": 1,
      "category_name": "Electronics & Gadgets",
      "vendor_name": "Audio World",
      "stock_quantity": 15,
      "in_stock": true
    }
  ]
}
```

API for Admin Dashboard: Toggle Category Status (Activate or Deactivate)
url: http://192.168.1.52:8000/admin-dashboard/categories/<category_id>/toggle-status/
method: POST

headers:
X-Requested-With: XMLHttpRequest (or standard browser form submission)

params:
none

response:
```json
{
  "success": true,
  "message": "Category 'Electronics & Gadgets' has been DEACTIVATED.",
  "category_id": 1,
  "status": "INACTIVE",
  "is_active": false
}
```


API for Product Search and Filtering
url: http://192.168.1.52:8000/api/user/products/search/
method: GET

headers:
none (public endpoint)

params (query parameters):
q: shirt (optional search keyword across name, description, sku, category, vendor)
category_id: 1 (optional category filter)
min_price: 500 (optional minimum price filter)
max_price: 2000 (optional maximum price filter)
in_stock: true (optional, true/1 to only include available inventory)
sort: price_low_to_high (options: price_low_to_high, price_high_to_low, newest; default: newest)
page: 1 (optional, default: 1)
limit: 20 (optional, default: 20, max: 100)

response:
```json
{
  "success": true,
  "query": "shirt",
  "total_matches": 15,
  "page": 1,
  "total_pages": 1,
  "has_next": false,
  "products": [
    {
      "id": 10,
      "name": "Cotton Casual Denim Shirt",
      "sku": "SKU-SHIRT-01",
      "price": 1200.0,
      "discount_price": 999.0,
      "image_url": "/media/products/shirt.jpg",
      "category_id": 1,
      "category_name": "Clothing & Apparel",
      "vendor_name": "Apex Fashion Hub",
      "stock_quantity": 15,
      "in_stock": true
    }
  ]
}
```

---

API for Random Public Products
url: http://192.168.1.52:8000/api/user/products/random/
alias: http://192.168.1.52:8000/api/products/random/
method: GET

headers:
none (public endpoint; no Authorization token required)

params (query parameters):
limit: 20 (optional, default: 20, minimum: 1, maximum: 100)
category_id: 1 (optional; must reference an active category)

response:
```json
{
  "success": true,
  "message": "Random products fetched successfully",
  "randomized": true,
  "total_available": 27,
  "returned_count": 20,
  "products": [
    {
      "id": 10,
      "name": "Cotton Casual Denim Shirt",
      "sku": "SKU-SHIRT-01",
      "price": 1200.0,
      "discount_price": 999.0,
      "effective_price": 999.0,
      "image_url": "/media/products/shirt.jpg",
      "category_id": 1,
      "category_name": "Clothing & Apparel",
      "vendor_id": 3,
      "vendor_name": "Apex Fashion Hub",
      "stock_quantity": 15,
      "in_stock": true,
      "has_variants": true,
      "variant_count": 4
    }
  ]
}
```

Only active, approved, in-stock products belonging to approved vendors are returned. Products assigned to inactive categories are excluded. The response is sent with no-cache headers and the database randomizes its order for every request.

---

API for Product Details
url: http://192.168.1.52:8000/api/user/products/<product_id>/
aliases:
- http://192.168.1.52:8000/api/user/product/detail/<product_id>/
- http://192.168.1.52:8000/api/products/<product_id>/
method: GET

headers:
none (public customer endpoint)

params:
none (path parameter: product_id)

response (successful product detail):
```json
{
  "success": true,
  "message": "Product details fetched successfully",
  "product": {
    "id": 10,
    "name": "Wireless Noise Cancelling Headphones",
    "sku": "PROD-203948",
    "description": "Premium over-ear wireless headphones with active noise cancellation and 30-hour battery life.",
    "price": 2999.0,
    "discount_price": 2499.0,
    "effective_price": 2499.0,
    "savings_amount": 500.0,
    "savings_percentage": 16.7,
    "stock_quantity": 20,
    "low_stock_threshold": 5,
    "unit": "Piece",
    "image_url": "/media/products/headphones.jpg",
    "status": "ACTIVE",
    "in_stock": true,
    "low_stock_warning": false,
    "is_approved": true,
    "category": {
      "id": 1,
      "name": "Electronics & Gadgets",
      "description": "Smartphones, audio, and accessories",
      "image_url": "/media/categories/images/electronics.jpg"
    },
    "vendor": {
      "id": 2,
      "vendor_code": "VND-4821",
      "business_name": "Apex Electronics Hub",
      "owner_name": "Siddharth Rao",
      "city": "Bengaluru",
      "state": "Karnataka",
      "store_logo": "/media/vendors/logos/audioworld.png"
    },
    "has_variants": true,
    "total_variants": 2,
    "available_colors": [
      "Black",
      "Silver"
    ],
    "available_sizes": [
      "Standard"
    ],
    "available_materials": [
      "Brushed Aluminum",
      "Matte Plastic"
    ],
    "variants": [
      {
        "id": 1,
        "product_id": 10,
        "title": "Midnight Black",
        "color": "Black",
        "size": "Standard",
        "material": "Matte Plastic",
        "sku": "PROD-203948-BLK",
        "price": 2999.0,
        "discount_price": 2499.0,
        "effective_price": 2499.0,
        "stock_quantity": 12,
        "in_stock": true,
        "image_url": "/media/products/headphones-black.jpg",
        "is_active": true
      },
      {
        "id": 2,
        "product_id": 10,
        "title": "Silver Edition",
        "color": "Silver",
        "size": "Standard",
        "material": "Brushed Aluminum",
        "sku": "PROD-203948-SLV",
        "price": 3299.0,
        "discount_price": 2699.0,
        "effective_price": 2699.0,
        "stock_quantity": 8,
        "in_stock": true,
        "image_url": "/media/products/headphones-silver.jpg",
        "is_active": true
      }
    ],
    "created_at": "2026-10-20T10:00:00+00:00",
    "updated_at": "2026-10-22T14:30:00+00:00"
  },
  "related_products": [
    {
      "id": 14,
      "name": "Desktop USB DAC & Headphone Amp",
      "sku": "PROD-819234",
      "price": 4500.0,
      "discount_price": 3999.0,
      "effective_price": 3999.0,
      "image_url": "/media/products/dac.jpg",
      "category_id": 1,
      "category_name": "Electronics & Gadgets",
      "vendor_name": "Apex Electronics Hub",
      "stock_quantity": 10,
      "in_stock": true
    }
  ]
}
```

response (if product is out of stock):
```json
{
  "success": true,
  "message": "Product details fetched successfully",
  "product": {
    "id": 12,
    "name": "Studio Reference Monitor Speakers",
    "sku": "PROD-992144",
    "description": "High-fidelity balanced studio monitors",
    "price": 8999.0,
    "discount_price": 7999.0,
    "effective_price": 7999.0,
    "savings_amount": 1000.0,
    "savings_percentage": 11.1,
    "stock_quantity": 0,
    "low_stock_threshold": 5,
    "unit": "Pair",
    "image_url": "/media/products/speakers.jpg",
    "status": "OUT_OF_STOCK",
    "in_stock": false,
    "low_stock_warning": false,
    "is_approved": true,
    "category": {
      "id": 1,
      "name": "Electronics & Gadgets"
    },
    "vendor": {
      "id": 2,
      "business_name": "Apex Electronics Hub"
    },
    "has_variants": false,
    "total_variants": 0,
    "variants": [],
    "created_at": "2026-10-21T09:15:00+00:00",
    "updated_at": "2026-10-23T08:00:00+00:00"
  },
  "related_products": []
}
```

response (if product not found, inactive, unapproved, vendor unapproved, or category inactive):
```json
{
  "success": false,
  "message": "Product with ID '999' was not found or is unavailable."
}
```
