API for Create Product
url: http://192.168.1.52:8000/api/vendor/product/create/
method: POST

headers:
Authorization: Bearer <vendor_token> (optional, automatically scopes to authenticated merchant store)

params:
name: Wireless Noise Cancelling Smart Watch Pro
sku: WATCH-PRO-001 (optional, auto-generated unique if left blank)
category_id: 2 (master category ID)
price: 3499.00
discount_price: 2999.00 (optional offer price)
stock_quantity: 50
unit: Piece (optional, default: Piece)
description: High-performance smartwatch featuring OLED display, health tracking, and 7-day battery life.
status: ACTIVE (choices: ACTIVE, INACTIVE, OUT_OF_STOCK)
image: [Upload binary image file, e.g. watch.jpg / png]

response:
{
  "success": true,
  "message": "Product created successfully",
  "product": {
    "id": 1,
    "vendor_id": 7,
    "vendor_name": "Kashmir Pashmina & Crafts",
    "vendor_code": "VEND-94847",
    "category_id": 2,
    "category_name": "Electronics & Appliances",
    "name": "Wireless Noise Cancelling Smart Watch Pro",
    "sku": "WATCH-PRO-001",
    "description": "High-performance smartwatch featuring OLED display, health tracking, and 7-day battery life.",
    "price": 3499.0,
    "discount_price": 2999.0,
    "stock_quantity": 50,
    "unit": "Piece",
    "image": "/media/products/smart_watch.png",
    "status": "ACTIVE",
    "is_approved": true,
    "created_at": "2026-10-17T05:12:37.568900+00:00",
    "updated_at": "2026-10-17T05:12:37.568922+00:00"
  }
}

API for List Products
url: http://192.168.1.52:8000/api/vendor/product/list/
method: GET

headers:
Authorization: Bearer <vendor_token> (optional, scopes product list to logged-in vendor)

params:
category_id: 2 (optional, filter by Category master ID)
category: Electronics (optional, filter by Category master name)
search: Watch (optional, search in product name, SKU, or description)
status: ACTIVE (optional, filter by ACTIVE, INACTIVE, OUT_OF_STOCK)
min_price: 2000 (optional, filter minimum price)
max_price: 4000 (optional, filter maximum price)
in_stock: true (optional, filter items where stock_quantity > 0)
ordering: -created_at (optional, choices: created_at, -created_at, price, -price, name, -name, stock_quantity, -stock_quantity)

response:
{
  "success": true,
  "count": 1,
  "products": [
    {
      "id": 1,
      "vendor_id": 7,
      "vendor_name": "Kashmir Pashmina & Crafts",
      "vendor_code": "VEND-94847",
      "category_id": 2,
      "category_name": "Electronics & Appliances",
      "name": "Wireless Noise Cancelling Smart Watch Pro",
      "sku": "WATCH-PRO-001",
      "description": "High-performance smartwatch featuring OLED display, health tracking, and 7-day battery life.",
      "price": 3499.0,
      "discount_price": 2999.0,
      "stock_quantity": 50,
      "unit": "Piece",
      "image": "/media/products/smart_watch.png",
      "status": "ACTIVE",
      "is_approved": true,
      "created_at": "2026-10-17T05:12:37.568900+00:00",
      "updated_at": "2026-10-17T05:12:37.568922+00:00"
    }
  ]
}

API for Get Product Details
url: http://192.168.1.52:8000/api/vendor/product/detail/1/
method: GET

params:
none

response:
{
  "success": true,
  "product": {
    "id": 1,
    "vendor_id": 7,
    "vendor_name": "Kashmir Pashmina & Crafts",
    "vendor_code": "VEND-94847",
    "category_id": 2,
    "category_name": "Electronics & Appliances",
    "name": "Wireless Noise Cancelling Smart Watch Pro",
    "sku": "WATCH-PRO-001",
    "description": "High-performance smartwatch featuring OLED display, health tracking, and 7-day battery life.",
    "price": 3499.0,
    "discount_price": 2999.0,
    "stock_quantity": 50,
    "unit": "Piece",
    "image": "/media/products/smart_watch.png",
    "status": "ACTIVE",
    "is_approved": true,
    "created_at": "2026-10-17T05:12:37.568900+00:00",
    "updated_at": "2026-10-17T05:12:37.568922+00:00"
  }
}

API for Update Product
url: http://192.168.1.52:8000/api/vendor/product/update/1/
method: POST

params:
price: 3199.00
discount_price: 2799.00
stock_quantity: 42
description: Updated: Now includes 2 additional magnetic bands and 10-day battery.
status: ACTIVE
image: [optional, new binary image file to update product photo]

response:
{
  "success": true,
  "message": "Product updated successfully",
  "product": {
    "id": 1,
    "vendor_id": 7,
    "vendor_name": "Kashmir Pashmina & Crafts",
    "vendor_code": "VEND-94847",
    "category_id": 2,
    "category_name": "Electronics & Appliances",
    "name": "Wireless Noise Cancelling Smart Watch Pro",
    "sku": "WATCH-PRO-001",
    "description": "Updated: Now includes 2 additional magnetic bands and 10-day battery.",
    "price": 3199.0,
    "discount_price": 2799.0,
    "stock_quantity": 42,
    "unit": "Piece",
    "image": "/media/products/smart_watch.png",
    "status": "ACTIVE",
    "is_approved": true,
    "created_at": "2026-10-17T05:12:37.568900+00:00",
    "updated_at": "2026-10-17T05:12:37.603566+00:00"
  }
}

API for Delete Product
url: http://192.168.1.52:8000/api/vendor/product/delete/1/
method: POST

params:
none

response:
{
  "success": true,
  "message": "Product 'Wireless Noise Cancelling Smart Watch Pro' (WATCH-PRO-001) deleted successfully.",
  "product_id": 1
}
