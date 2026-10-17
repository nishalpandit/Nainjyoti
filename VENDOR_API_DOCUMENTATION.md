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

url: http://192.168.1.52:8000/api/vendor/logout/
method: POST

headers:
Authorization: Bearer 2681b2de4fc8d35174f795e7b9cf7646f39a7eeb62178e1eb2568bf9040377f7

response:
{
  "success": true,
  "message": "Vendor successfully logged out"
}
