API for Vendor Registration
url: http://192.168.1.52:8000/api/vendor/register/
method: POST

params:
business_name: Kashmir Pashmina & Crafts
owner_name: Farooq Ahmed
email: merchant@crafts.in
phone: 9876543210
password: SellerSecure@2026
business_type: Manufacturer & Artisan
category: Handicrafts & Handlooms
address: 42 Heritage Arts Lane, Old City
city: Srinagar
state: Jammu and Kashmir
pincode: 190001
gst_number: 01AAAAA0000A1Z5
pan_number: ABCDE1234F
bank_name: HDFC Bank
account_number: 50100492817291
ifsc_code: HDFC0000123
gst_document: optional file
pan_document: optional file
id_proof: optional file

response:
{
  "success": true,
  "message": "Vendor registration submitted successfully! Your application is under compliance review.",
  "vendor_code": "VEND-15384",
  "status": "PENDING",
  "token": "123b48ab6ccd78e7a46b8971b9630599ed65db4ac3a21b5f56f66d9d666e69b6",
  "vendor": {
    "id": 4,
    "vendor_code": "VEND-15384",
    "business_name": "Kashmir Pashmina & Crafts",
    "owner_name": "Farooq Ahmed",
    "email": "merchant@crafts.in",
    "phone": "9876543210",
    "business_type": "Manufacturer & Artisan",
    "category": "Handicrafts & Handlooms",
    "status": "PENDING",
    "status_display": "Pending Approval",
    "rejection_reason": "",
    "gst_number": "01AAAAA0000A1Z5",
    "pan_number": "ABCDE1234F",
    "bank_name": "HDFC Bank",
    "account_number": "50100492817291",
    "ifsc_code": "HDFC0000123",
    "address": "42 Heritage Arts Lane, Old City",
    "city": "Srinagar",
    "state": "Jammu and Kashmir",
    "pincode": "190001",
    "created_at": "2026-10-16T11:39:27.821707+00:00"
  }
}

API for Vendor Login
url: http://192.168.1.52:8000/api/vendor/login/
method: POST

params:
username: merchant@crafts.in
password: SellerSecure@2026

response:
{
  "success": true,
  "message": "Login successful. Welcome back to your seller console, Kashmir Pashmina & Crafts!",
  "status": "APPROVED",
  "role": "VENDOR",
  "token": "123b48ab6ccd78e7a46b8971b9630599ed65db4ac3a21b5f56f66d9d666e69b6",
  "vendor": {
    "id": 4,
    "vendor_code": "VEND-15384",
    "business_name": "Kashmir Pashmina & Crafts",
    "owner_name": "Farooq Ahmed",
    "email": "merchant@crafts.in",
    "phone": "9876543210",
    "business_type": "Manufacturer & Artisan",
    "category": "Handicrafts & Handlooms",
    "status": "APPROVED",
    "status_display": "Approved"
  }
}

API for Vendor Application Status
url: http://192.168.1.52:8000/api/vendor/status/?code=VEND-15384
method: GET

response:
{
  "success": true,
  "vendor_code": "VEND-15384",
  "business_name": "Kashmir Pashmina & Crafts",
  "owner_name": "Farooq Ahmed",
  "status": "PENDING",
  "status_display": "Pending Approval",
  "rejection_reason": null,
  "submitted_at": "2026-10-16T11:39:27.821707+00:00",
  "updated_at": "2026-10-16T11:39:27.821733+00:00"
}

API for Get Vendor Profile
url: http://192.168.1.52:8000/api/vendor/profile/
method: GET

headers:
Authorization: Bearer edcdf99aed5acc14491cd5d376e9dba74b4661b2bc70da69c2082fd4cc3409f8

response:
{
  "success": true,
  "vendor": {
    "id": 6,
    "vendor_code": "VEND-85140",
    "business_name": "Kashmir Pashmina & Crafts",
    "owner_name": "Farooq Ahmed",
    "email": "merchant@crafts.in",
    "support_email": "support@crafts.in",
    "phone": "9876543210",
    "business_type": "Manufacturer & Artisan",
    "category": "Handicrafts & Handlooms",
    "store_description": "Finest handwoven Pashmina shawls, artisanal stoles, and traditional Kashmiri handicrafts.",
    "store_logo": "http://192.168.1.52:8000/media/vendor_documents/logos/store_logo.png",
    "store_banner": "http://192.168.1.52:8000/media/vendor_documents/banners/banner.png",
    "status": "APPROVED",
    "status_display": "Approved",
    "rejection_reason": "",
    "gst_number": "01AAAAA0000A1Z5",
    "pan_number": "ABCDE1234F",
    "bank_name": "HDFC Bank",
    "account_number": "50100492817291",
    "ifsc_code": "HDFC0000123",
    "address": "42 Heritage Arts Lane, Old City",
    "city": "Srinagar",
    "state": "Jammu and Kashmir",
    "pincode": "190001",
    "gst_document": "http://192.168.1.52:8000/media/vendor_documents/gst/gst_cert.pdf",
    "pan_document": "http://192.168.1.52:8000/media/vendor_documents/pan/pan_card.pdf",
    "id_proof": "http://192.168.1.52:8000/media/vendor_documents/id_proof/aadhar.pdf",
    "created_at": "2026-10-16T12:25:29.774120+00:00",
    "updated_at": "2026-10-16T12:25:31.709323+00:00"
  }
}

API for Update Vendor Profile
url: http://192.168.1.52:8000/api/vendor/profile/
method: POST

headers:
Authorization: Bearer edcdf99aed5acc14491cd5d376e9dba74b4661b2bc70da69c2082fd4cc3409f8

params:
business_name: Kashmir Pashmina & Royal Silk Co.
owner_name: Farooq Ahmed
phone: 9876543210
support_email: support@crafts.in
store_description: Finest handwoven Pashmina shawls, artisanal stoles, and traditional Kashmiri handicrafts.
category: Handicrafts & Handlooms
business_type: Manufacturer & Artisan
address: 42 Heritage Arts Lane, Old City
city: Srinagar
state: Jammu and Kashmir
pincode: 190001
bank_name: State Bank of India
account_number: 30199482710
ifsc_code: SBIN0001234
gst_number: 01AAAAA0000A1Z5
pan_number: ABCDE1234F

response:
{
  "success": true,
  "message": "Store profile updated successfully",
  "vendor": {
    "id": 6,
    "vendor_code": "VEND-85140",
    "business_name": "Kashmir Pashmina & Royal Silk Co.",
    "owner_name": "Farooq Ahmed",
    "email": "merchant@crafts.in",
    "support_email": "support@crafts.in",
    "phone": "9876543210",
    "status": "APPROVED"
  }
}

API for Vendor Change Password
url: http://192.168.1.52:8000/api/vendor/profile/change-password/
method: POST

headers:
Authorization: Bearer edcdf99aed5acc14491cd5d376e9dba74b4661b2bc70da69c2082fd4cc3409f8

params:
current_password: SellerSecure@2026
new_password: BrandNewPassword@2026

response:
{
  "success": true,
  "message": "Password updated successfully. New token generated.",
  "token": "2681b2de4fc8d35174f795e7b9cf7646f39a7eeb62178e1eb2568bf9040377f7"
}

API for Vendor Logout
url: http://192.168.1.52:8000/api/vendor/logout/
method: POST

headers:
Authorization: Bearer 2681b2de4fc8d35174f795e7b9cf7646f39a7eeb62178e1eb2568bf9040377f7

response:
{
  "success": true,
  "message": "Vendor successfully logged out"
}

API for Vendor Create Category
url: http://192.168.1.52:8000/api/vendor/category/create/
method: POST

params:
name: Handmade Wooden Carvings
description: Authentic walnut wood and deodar handcrafted decorative art pieces
commission_rate: 8.00
icon: fa-tree
display_order: 3
is_active: true

response:
{
  "success": true,
  "message": "Category created successfully",
  "category": {
    "id": 7,
    "name": "Handmade Wooden Carvings",
    "slug": "handmade-wooden-carvings",
    "description": "Authentic walnut wood and deodar handcrafted decorative art pieces",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-tree",
    "commission_rate": 8.0,
    "display_order": 3,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:45:07.135766+00:00",
    "updated_at": "2026-10-17T04:45:07.135799+00:00",
    "subcategories": []
  }
}

API for Vendor Create Subcategory
url: http://192.168.1.52:8000/api/vendor/category/create/
method: POST

params:
name: Walnut Jewelry Boxes
description: Intricately carved Kashmiri walnut wood jewelry boxes with brass inlays
parent_id: 7
commission_rate: 9.50
icon: fa-gem
display_order: 1
is_active: true

response:
{
  "success": true,
  "message": "Category created successfully",
  "category": {
    "id": 8,
    "name": "Walnut Jewelry Boxes",
    "slug": "walnut-jewelry-boxes",
    "description": "Intricately carved Kashmiri walnut wood jewelry boxes with brass inlays",
    "parent_id": 7,
    "parent_name": "Handmade Wooden Carvings",
    "image": null,
    "icon": "fa-gem",
    "commission_rate": 9.5,
    "display_order": 1,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:45:07.165842+00:00",
    "updated_at": "2026-10-17T04:45:07.165866+00:00",
    "subcategories": []
  }
}

API for Vendor List Categories
url: http://192.168.1.52:8000/api/vendor/category/list/
method: GET

params:
none

response:
{
  "success": true,
  "count": 5,
  "categories": [
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "slug": "fashion-textiles",
      "description": "Updated: Premium ethnic wear, fabrics, apparel, Kashmiri shawls and modern fashion",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-shirt",
      "commission_rate": 9.5,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 2,
      "created_at": "2026-10-17T04:34:09.012458+00:00",
      "updated_at": "2026-10-17T04:37:34.865589+00:00"
    },
    {
      "id": 3,
      "name": "Kashmiri Shawls & Stoles",
      "slug": "kashmiri-shawls-stoles",
      "description": "Authentic hand-woven Pashmina, Cashmere and embroidered woollen shawls",
      "parent_id": 1,
      "parent_name": "Fashion & Textiles",
      "image": null,
      "icon": "fa-vest",
      "commission_rate": 12.0,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.070945+00:00",
      "updated_at": "2026-10-17T04:34:09.070967+00:00"
    },
    {
      "id": 2,
      "name": "Electronics & Appliances",
      "slug": "electronics-appliances",
      "description": "Smartphones, home appliances, wearable devices and smart gadgets",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-laptop",
      "commission_rate": 7.5,
      "display_order": 2,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.041989+00:00",
      "updated_at": "2026-10-17T04:34:09.042016+00:00"
    },
    {
      "id": 4,
      "name": "Handcrafted Silk Sarees",
      "slug": "handcrafted-silk-sarees",
      "description": "Traditional banarasi, chanderi, and pure silk heritage sarees",
      "parent_id": 1,
      "parent_name": "Fashion & Textiles",
      "image": null,
      "icon": "fa-ribbon",
      "commission_rate": 10.0,
      "display_order": 2,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.100814+00:00",
      "updated_at": "2026-10-17T04:34:09.100835+00:00"
    },
    {
      "id": 7,
      "name": "Handmade Wooden Carvings",
      "slug": "handmade-wooden-carvings",
      "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-tree",
      "commission_rate": 7.5,
      "display_order": 3,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:45:07.135766+00:00",
      "updated_at": "2026-10-17T04:45:07.218529+00:00"
    }
  ]
}

API for Vendor Category Hierarchy Tree
url: http://192.168.1.52:8000/api/vendor/category/tree/
method: GET

params:
none

response:
{
  "success": true,
  "count": 3,
  "tree": [
    {
      "id": 1,
      "name": "Fashion & Textiles",
      "slug": "fashion-textiles",
      "description": "Updated: Premium ethnic wear, fabrics, apparel, Kashmiri shawls and modern fashion",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-shirt",
      "commission_rate": 9.5,
      "display_order": 1,
      "is_active": true,
      "subcategories_count": 2,
      "created_at": "2026-10-17T04:34:09.012458+00:00",
      "updated_at": "2026-10-17T04:37:34.865589+00:00",
      "subcategories": [
        {
          "id": 3,
          "name": "Kashmiri Shawls & Stoles",
          "slug": "kashmiri-shawls-stoles",
          "description": "Authentic hand-woven Pashmina, Cashmere and embroidered woollen shawls",
          "parent_id": 1,
          "parent_name": "Fashion & Textiles",
          "image": null,
          "icon": "fa-vest",
          "commission_rate": 12.0,
          "display_order": 1,
          "is_active": true,
          "subcategories_count": 0,
          "created_at": "2026-10-17T04:34:09.070945+00:00",
          "updated_at": "2026-10-17T04:34:09.070967+00:00"
        },
        {
          "id": 4,
          "name": "Handcrafted Silk Sarees",
          "slug": "handcrafted-silk-sarees",
          "description": "Traditional banarasi, chanderi, and pure silk heritage sarees",
          "parent_id": 1,
          "parent_name": "Fashion & Textiles",
          "image": null,
          "icon": "fa-ribbon",
          "commission_rate": 10.0,
          "display_order": 2,
          "is_active": true,
          "subcategories_count": 0,
          "created_at": "2026-10-17T04:34:09.100814+00:00",
          "updated_at": "2026-10-17T04:34:09.100835+00:00"
        }
      ]
    },
    {
      "id": 2,
      "name": "Electronics & Appliances",
      "slug": "electronics-appliances",
      "description": "Smartphones, home appliances, wearable devices and smart gadgets",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-laptop",
      "commission_rate": 7.5,
      "display_order": 2,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:34:09.041989+00:00",
      "updated_at": "2026-10-17T04:34:09.042016+00:00",
      "subcategories": []
    },
    {
      "id": 7,
      "name": "Handmade Wooden Carvings",
      "slug": "handmade-wooden-carvings",
      "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
      "parent_id": null,
      "parent_name": null,
      "image": null,
      "icon": "fa-tree",
      "commission_rate": 7.5,
      "display_order": 3,
      "is_active": true,
      "subcategories_count": 0,
      "created_at": "2026-10-17T04:45:07.135766+00:00",
      "updated_at": "2026-10-17T04:45:07.218529+00:00",
      "subcategories": []
    }
  ]
}

API for Vendor Get Category Details
url: http://192.168.1.52:8000/api/vendor/category/detail/7/
method: GET

params:
none

response:
{
  "success": true,
  "category": {
    "id": 7,
    "name": "Handmade Wooden Carvings",
    "slug": "handmade-wooden-carvings",
    "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-tree",
    "commission_rate": 7.5,
    "display_order": 3,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:45:07.135766+00:00",
    "updated_at": "2026-10-17T04:45:07.218529+00:00",
    "subcategories": []
  }
}

API for Vendor Update Category
url: http://192.168.1.52:8000/api/vendor/category/update/7/
method: POST

params:
commission_rate: 7.50
description: Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art
icon: fa-tree

response:
{
  "success": true,
  "message": "Category updated successfully",
  "category": {
    "id": 7,
    "name": "Handmade Wooden Carvings",
    "slug": "handmade-wooden-carvings",
    "description": "Updated: Premium authentic walnut wood and deodar handcrafted heritage decorative art",
    "parent_id": null,
    "parent_name": null,
    "image": null,
    "icon": "fa-tree",
    "commission_rate": 7.5,
    "display_order": 3,
    "is_active": true,
    "subcategories_count": 0,
    "created_at": "2026-10-17T04:45:07.135766+00:00",
    "updated_at": "2026-10-17T04:45:07.218529+00:00"
  }
}

API for Vendor Soft Delete Category
url: http://192.168.1.52:8000/api/vendor/category/delete/8/?soft=true
method: POST

params:
soft: true

response:
{
  "success": true,
  "message": "Category 'Walnut Jewelry Boxes' marked as inactive (soft deleted).",
  "category_id": 8,
  "is_active": false
}

API for Vendor Delete Category
url: http://192.168.1.52:8000/api/vendor/category/delete/8/
method: POST

params:
none

response:
{
  "success": true,
  "message": "Category 'Walnut Jewelry Boxes' (ID: 8) deleted successfully.",
  "category_id": 8
}

