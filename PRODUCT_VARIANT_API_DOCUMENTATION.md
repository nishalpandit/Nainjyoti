# Product and Variant API Documentation

Base URL: `http://192.168.1.52:8000`

## Vendor: Create Product

url: http://192.168.1.52:8000/api/vendor/product/create/
method: POST

headers:
Authorization: Bearer VENDOR_TOKEN
Content-Type: multipart/form-data

params:
name: Cotton Casual Denim Shirt
category_id: 1
price: 999
discount_price: 899
stock_quantity: 0
sku: SHIRT-001
description: Cotton casual shirt with selectable colors and sizes
unit: Piece
image: [binary image file]

response:
```json
{
  "success": true,
  "message": "Product created successfully",
  "product": {
    "id": 60,
    "name": "Cotton Casual Denim Shirt",
    "sku": "SHIRT-001",
    "price": 999.0,
    "discount_price": 899.0,
    "effective_price": 899.0,
    "stock_quantity": 0,
    "has_variants": false,
    "variant_count": 0
  }
}
```

Admin product creation uses the same params:

url: http://192.168.1.52:8000/api/admin/product/create/
method: POST

Additional required admin param when selecting the owner:
vendor_id: 1

## Vendor: Create Product Variant

url: http://192.168.1.52:8000/api/vendor/products/60/variants/create/
method: POST

headers:
Authorization: Bearer VENDOR_TOKEN
Content-Type: multipart/form-data

### Single Variant Creation:
params:
title: Midnight Blue / Large
color: Blue
size: L
material: Cotton
sku: SHIRT-001-L-BLU
price: 999
discount_price: 799
stock_quantity: 20
images: [multiple binary image files]
is_active: true

### Color-based Multi-Size Creation (1-by-1 Sizes & Multi-Image Gallery):
params:
color: Crimson Red
material: Pure Cotton
price: 999 (default selling price, optional)
discount_price: 799 (default sale price, optional)
sizes: JSON string array of sizes added 1 by 1:
```json
[
  {"size": "S", "stock_quantity": 15, "price": "999.00", "discount_price": "799.00"},
  {"size": "M", "stock_quantity": 25, "price": "999.00", "discount_price": "799.00"},
  {"size": "L", "stock_quantity": 20, "price": "1049.00", "discount_price": "849.00"},
  {"size": "XL", "stock_quantity": 10, "price": "1099.00", "discount_price": "899.00"}
]
```
images: [multiple binary image files: front, back, angle, detail]
is_active: true

response:
```json
{
  "success": true,
  "message": "Successfully created 4 variant(s) for 'Crimson Red'.",
  "created_count": 4,
  "variants": [
    {
      "id": 10,
      "product_id": 60,
      "title": "Cotton Casual Denim Shirt - Crimson Red (S)",
      "color": "Crimson Red",
      "size": "S",
      "material": "Pure Cotton",
      "sku": "SHIRT-001-S-RED",
      "price": 999.0,
      "discount_price": 799.0,
      "effective_price": 799.0,
      "stock_quantity": 15,
      "in_stock": true,
      "image_url": "/media/variants/crimson_front.jpg",
      "images": [
        "/media/variants/crimson_front.jpg",
        "/media/variants/crimson_back.jpg"
      ],
      "is_active": true
    }
  ],
  "product_stock_quantity": 70
}
```

Admin alias:

url: http://192.168.1.52:8000/api/admin/products/60/variants/create/
method: POST

params and response are identical to the vendor endpoint.

## Vendor: Delete Variant Gallery Image

url: http://192.168.1.52:8000/api/vendor/variants/images/{image_id}/delete/
method: POST

headers:
Authorization: Bearer VENDOR_TOKEN

response:
```json
{
  "success": true,
  "message": "Variant image deleted successfully."
}
```

Admin alias:
url: http://192.168.1.52:8000/api/admin/variants/images/{image_id}/delete/
method: POST

## Vendor: List Product Variants

url: http://192.168.1.52:8000/api/vendor/products/60/variants/
method: GET

headers:
Authorization: Bearer VENDOR_TOKEN

params:
No body params

response:
```json
{
  "success": true,
  "product_id": 60,
  "product_name": "Cotton Casual Denim Shirt",
  "total_variants": 4,
  "color_groups": [
    {
      "color": "Crimson Red",
      "total_stock": 70,
      "images": [
        "/media/variants/crimson_front.jpg",
        "/media/variants/crimson_back.jpg"
      ],
      "variants": [
        {
          "id": 10,
          "product_id": 60,
          "title": "Cotton Casual Denim Shirt - Crimson Red (S)",
          "color": "Crimson Red",
          "size": "S",
          "material": "Pure Cotton",
          "sku": "SHIRT-001-S-RED",
          "price": 999.0,
          "discount_price": 799.0,
          "effective_price": 799.0,
          "stock_quantity": 15,
          "in_stock": true,
          "image_url": "/media/variants/crimson_front.jpg",
          "images": [
            "/media/variants/crimson_front.jpg",
            "/media/variants/crimson_back.jpg"
          ],
          "is_active": true
        }
      ]
    }
  ],
  "variants": [ ... ]
}
```

Admin alias:

url: http://192.168.1.52:8000/api/admin/products/60/variants/
method: GET

## Vendor: Variant Detail

url: http://192.168.1.52:8000/api/vendor/variants/10/
method: GET

headers:
Authorization: Bearer VENDOR_TOKEN

params:
No body params

response:
```json
{
  "success": true,
  "variant": {
    "id": 10,
    "product_id": 60,
    "title": "Midnight Blue / Large",
    "color": "Blue",
    "size": "L",
    "material": "Cotton",
    "sku": "SHIRT-001-L-BLU",
    "price": 999.0,
    "discount_price": 799.0,
    "effective_price": 799.0,
    "stock_quantity": 20,
    "in_stock": true,
    "image_url": "/media/products/variants/shirt-blue-large.jpg",
    "is_active": true
  }
}
```

Admin alias:

url: http://192.168.1.52:8000/api/admin/variants/10/
method: GET

## Vendor: Update Product Variant

url: http://192.168.1.52:8000/api/vendor/variants/10/update/
method: POST

headers:
Authorization: Bearer VENDOR_TOKEN
Content-Type: multipart/form-data

params (send one or more):
title: Midnight Blue / Extra Large
color: Blue
size: XL
material: Cotton
sku: SHIRT-001-XL-BLU
price: 1099
discount_price: 849
stock_quantity: 25
image: [binary image file]
remove_image: false
is_active: true

response:
```json
{
  "success": true,
  "message": "Product variant updated successfully",
  "variant": {
    "id": 10,
    "product_id": 60,
    "title": "Midnight Blue / Extra Large",
    "color": "Blue",
    "size": "XL",
    "material": "Cotton",
    "sku": "SHIRT-001-XL-BLU",
    "price": 1099.0,
    "discount_price": 849.0,
    "effective_price": 849.0,
    "stock_quantity": 25,
    "in_stock": true,
    "image_url": "/media/products/variants/shirt-blue-xl.jpg",
    "is_active": true
  },
  "product_stock_quantity": 25
}
```

Admin alias:

url: http://192.168.1.52:8000/api/admin/variants/10/update/
method: POST

## Vendor: Delete Product Variant

url: http://192.168.1.52:8000/api/vendor/variants/10/delete/
method: DELETE

headers:
Authorization: Bearer VENDOR_TOKEN

params:
No body params

response:
```json
{
  "success": true,
  "message": "Product variant deleted successfully",
  "deleted_variant_id": 10,
  "deleted_variant_title": "Midnight Blue / Extra Large",
  "product_stock_quantity": 0
}
```

Admin alias:

url: http://192.168.1.52:8000/api/admin/variants/10/delete/
method: DELETE

## Customer: Product Variants

url: http://192.168.1.52:8000/api/user/products/60/variants/
method: GET

params:
No body params

response:
```json
{
  "success": true,
  "product_id": 60,
  "product_name": "Cotton Casual Denim Shirt",
  "total_variants": 2,
  "available_colors": ["Black", "Blue"],
  "available_sizes": ["L", "XL"],
  "available_materials": ["Cotton"],
  "variants": [
    {
      "id": 10,
      "product_id": 60,
      "title": "Midnight Blue / Large",
      "color": "Blue",
      "size": "L",
      "material": "Cotton",
      "sku": "SHIRT-001-L-BLU",
      "price": 999.0,
      "discount_price": 799.0,
      "effective_price": 799.0,
      "stock_quantity": 20,
      "in_stock": true,
      "image_url": "/media/products/variants/shirt-blue-large.jpg",
      "is_active": true
    }
  ]
}
```

## Customer: Variant Detail

url: http://192.168.1.52:8000/api/user/variants/10/
method: GET

params:
No body params

response:
```json
{
  "success": true,
  "variant": {
    "id": 10,
    "product_id": 60,
    "title": "Midnight Blue / Large",
    "color": "Blue",
    "size": "L",
    "material": "Cotton",
    "sku": "SHIRT-001-L-BLU",
    "price": 999.0,
    "discount_price": 799.0,
    "effective_price": 799.0,
    "stock_quantity": 20,
    "in_stock": true,
    "image_url": "/media/products/variants/shirt-blue-large.jpg",
    "is_active": true
  }
}
```

## Variant Stock Adjustment

url: http://192.168.1.52:8000/api/vendor/stock/update/60/
method: POST

headers:
Authorization: Bearer VENDOR_TOKEN
Content-Type: multipart/form-data

params:
variant_id: 10
action: ADD
quantity: 5
movement_type: RESTOCK
reason: New warehouse stock received
reference_id: PO-2026-104

response:
```json
{
  "success": true,
  "message": "Stock for variant 'Midnight Blue / Large' adjusted from 20 to 25 units.",
  "product": {
    "id": 60,
    "stock_quantity": 40,
    "has_variants": true,
    "variant_count": 2
  },
  "variant": {
    "id": 10,
    "stock_quantity": 25,
    "in_stock": true
  },
  "log": {
    "variant_id": 10,
    "quantity_changed": 5,
    "previous_stock": 20,
    "new_stock": 25
  }
}
```

Admin stock alias:

url: http://192.168.1.52:8000/api/admin/stock/update/60/
method: POST

## Updated Existing Customer APIs

Product search:
GET http://192.168.1.52:8000/api/user/products/search/

Category products:
GET http://192.168.1.52:8000/api/user/categories/<category_id>/products/

Product detail:
GET http://192.168.1.52:8000/api/user/products/<product_id>/

These responses now include variant-aware `effective_price`, `stock_quantity`, `in_stock`, `has_variants`, and `variant_count`. Product detail also includes the active `variants` collection and available option summaries.

For products with variants, product-level stock edits return an error. Send `variant_id` to the stock update API instead. Products without variants remain fully backward-compatible.
