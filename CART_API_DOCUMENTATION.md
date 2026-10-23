# Add to Cart API

## Add product or variant to cart

```text
url: http://192.168.1.52:8000/api/user/cart/add/
method: POST
authentication: Bearer token required
content-type: application/json
```

### Headers

```text
Authorization: Bearer <customer_token>
Content-Type: application/json
```

### Params for a product with variants

```json
{
  "product_id": 81,
  "variant_id": 16,
  "quantity": 1
}
```

### Params for a product without variants

```json
{
  "product_id": 84,
  "quantity": 1
}
```

`quantity` defaults to `1`. When the same product and variant are added again,
the requested quantity is added to the quantity already in the cart.

### Success response

```json
{
  "success": true,
  "message": "Product added to cart successfully.",
  "cart_item": {
    "id": 1,
    "product_id": 81,
    "product_name": "Wireless Noise Cancelling Headphones",
    "product_sku": "SKU-HEADPHONE-01",
    "variant_id": 16,
    "variant_title": "Midnight Black",
    "variant_sku": "SKU-HEADPHONE-01-BLK",
    "color": "Black",
    "size": "Standard",
    "material": "Matte Plastic",
    "image_url": null,
    "regular_price": 2999.0,
    "effective_price": 2499.0,
    "quantity": 1,
    "line_total": 2499.0,
    "savings": 500.0,
    "available_stock": 12,
    "in_stock": true,
    "created_at": "2026-10-23T07:44:28.945726+00:00",
    "updated_at": "2026-10-23T07:44:28.945754+00:00"
  },
  "cart": {
    "item_count": 1,
    "total_quantity": 1,
    "regular_subtotal": 2999.0,
    "discount": 500.0,
    "total": 2499.0,
    "items": [
      {
        "id": 1,
        "product_id": 81,
        "product_name": "Wireless Noise Cancelling Headphones",
        "product_sku": "SKU-HEADPHONE-01",
        "variant_id": 16,
        "variant_title": "Midnight Black",
        "variant_sku": "SKU-HEADPHONE-01-BLK",
        "color": "Black",
        "size": "Standard",
        "material": "Matte Plastic",
        "image_url": null,
        "regular_price": 2999.0,
        "effective_price": 2499.0,
        "quantity": 1,
        "line_total": 2499.0,
        "savings": 500.0,
        "available_stock": 12,
        "in_stock": true,
        "created_at": "2026-10-23T07:44:28.945726+00:00",
        "updated_at": "2026-10-23T07:44:28.945754+00:00"
      }
    ]
  }
}
```

### Important validation responses

- `401`: Customer Bearer token is missing or invalid.
- `403`: The customer account is deactivated.
- `404`: Product or selected active variant does not exist.
- `400`: Invalid IDs or quantity, unavailable product, missing variant selection,
  out-of-stock item, or requested quantity exceeds available stock.

---

## Next Step: Checkout & Payment
For converting the cart into an order and completing payment via COD or Online payment, refer to [CHECKOUT_PAYMENT_API_DOCUMENTATION.md](file:///c:/Users/PC/Desktop/Nainjyoti/CHECKOUT_PAYMENT_API_DOCUMENTATION.md).

