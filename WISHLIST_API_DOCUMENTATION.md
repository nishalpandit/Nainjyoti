# Wishlist API

All wishlist endpoints require the customer Bearer token:

```text
Authorization: Bearer <customer_token>
```

## 1. Add product to wishlist

```text
url: http://192.168.1.52:8000/api/user/wishlist/add/
method: POST
content-type: application/json
```

Params:

```json
{
  "product_id": 81,
  "variant_id": 16
}
```

For products that have variants, `variant_id` is required so the wishlist
remembers the selected color, size, material, SKU, image, price, and stock.
For a product without variants, send only `product_id`.

Response for a newly added product (`201 Created`):

```json
{
  "success": true,
  "message": "Product added to wishlist successfully.",
  "already_exists": false,
  "wishlist_item": {
    "id": 1,
    "product_id": 81,
    "name": "Wireless Noise Cancelling Headphones",
    "sku": "SKU-HEADPHONE-01",
    "variant_id": 16,
    "variant_title": "Midnight Black",
    "variant_sku": "SKU-HEADPHONE-01-BLK",
    "color": "Black",
    "size": "Standard",
    "material": "Matte Plastic",
    "description": "Premium over-ear wireless headphones with active noise cancellation and 30-hour battery life.",
    "price": 2999.0,
    "discount_price": 2499.0,
    "effective_price": 2499.0,
    "image_url": null,
    "category_id": 40,
    "category_name": "Details Test Cat Active",
    "vendor_id": 29,
    "vendor_name": "Apex Electronics Hub",
    "stock_quantity": 12,
    "in_stock": true,
    "has_variants": true,
    "variant_count": 2,
    "is_available": true,
    "added_at": "2026-10-23T07:52:20.949262+00:00"
  },
  "total_items": 1
}
```

Adding the same product and variant again does not create a duplicate. It
returns `200 OK` with `"already_exists": true`. Different variants of the
same product are saved as separate wishlist items.

## 2. List wishlist

```text
url: http://192.168.1.52:8000/api/user/wishlist/
method: GET
params: No body params
```

Response:

```json
{
  "success": true,
  "total_items": 1,
  "wishlist": [
    {
      "id": 1,
      "product_id": 81,
      "name": "Wireless Noise Cancelling Headphones",
      "sku": "SKU-HEADPHONE-01",
      "variant_id": 16,
      "variant_title": "Midnight Black",
      "variant_sku": "SKU-HEADPHONE-01-BLK",
      "color": "Black",
      "size": "Standard",
      "material": "Matte Plastic",
      "price": 2999.0,
      "discount_price": 2499.0,
      "effective_price": 2499.0,
      "stock_quantity": 12,
      "in_stock": true,
      "has_variants": true,
      "variant_count": 2,
      "is_available": true
    }
  ]
}
```

The live response contains all product, category, vendor, image, availability,
and timestamp fields shown by the add response.

## 3. Remove an exact variant from wishlist

```text
url: http://192.168.1.52:8000/api/user/wishlist/remove/<product_id>/variant/<variant_id>/
method: DELETE
params: No body params
```

Example:

```text
http://192.168.1.52:8000/api/user/wishlist/remove/81/variant/16/
```

Response:

```json
{
  "success": true,
  "message": "Product removed from wishlist successfully.",
  "removed_wishlist_item_id": 2,
  "product_id": 81,
  "variant_id": 16,
  "total_items": 0
}
```

For a product without variants, use:

```text
DELETE http://192.168.1.52:8000/api/user/wishlist/remove/<product_id>/
```

`POST` is also accepted by both remove routes for clients that cannot send an
HTTP `DELETE` request.

## Validation

- `401`: Missing or invalid customer token.
- `403`: Deactivated customer account.
- `404`: Product does not exist or is not in this customer's wishlist.
- `400`: Invalid product ID or product unavailable for customers.
