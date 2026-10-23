API for Checkout (Cash on Delivery - COD)
url: http://192.168.1.52:8000/api/user/checkout/
method: POST

headers:
Authorization: Bearer <customer_token>
Content-Type: application/json

params:
{
  "address_id": 1,
  "payment_method": "COD"
}

response:
```json
{
  "success": true,
  "message": "Order placed successfully. Payment will be collected on delivery.",
  "order": {
    "id": 14,
    "order_number": "ORD-20261023-4542",
    "customer": {
      "id": 2,
      "full_name": "Ananya Iyer",
      "phone": "9876543211",
      "email": "ananya@example.com"
    },
    "total_amount": 49997.0,
    "payment_method": "COD",
    "payment_status": "PENDING",
    "status": "PENDING",
    "status_display": "Pending Confirmation",
    "item_count": 2,
    "items": [
      {
        "id": 22,
        "product_id": 81,
        "product_name": "Flagship Smartphone Pro",
        "product_sku": "SKU-PHONE-X1-BLK",
        "variant_id": 16,
        "variant_title": "Space Black 256GB",
        "price": 46999.0,
        "quantity": 1,
        "total_price": 46999.0,
        "status": "PENDING"
      },
      {
        "id": 23,
        "product_id": 84,
        "product_name": "65W Fast GaN Charger",
        "product_sku": "SKU-CHARGER-65W",
        "variant_id": null,
        "variant_title": "",
        "price": 1499.0,
        "quantity": 2,
        "total_price": 2998.0,
        "status": "PENDING"
      }
    ],
    "created_at": "2026-10-23T14:50:00+00:00"
  },
  "payment": {
    "id": 5,
    "reference": "PAY-20261023-A89F0E12",
    "method": "COD",
    "amount": 49997.0,
    "currency": "INR",
    "status": "PENDING",
    "requires_online_payment": false
  },
  "delivery_address": {
    "id": 1,
    "full_name": "Ananya Iyer",
    "phone": "9876543211",
    "address_line_1": "12, MG Road, Apartment 4B",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
    "country": "India"
  },
  "cart_cleared": true
}
```

response (if cart is empty):
```json
{
  "success": false,
  "message": "Your cart is empty. Add at least one item before checkout."
}
```

response (if address not found):
```json
{
  "success": false,
  "message": "Address with ID '99' was not found for this customer."
}
```

response (if stock is insufficient):
```json
{
  "success": false,
  "message": "Only 1 item(s) of 'Flagship Smartphone Pro' are available.",
  "cart_item_id": 12,
  "available_stock": 1,
  "requested_quantity": 2
}
```


API for Checkout (Online Payment)
url: http://192.168.1.52:8000/api/user/checkout/
method: POST

headers:
Authorization: Bearer <customer_token>
Content-Type: application/json

params:
{
  "address_id": 1,
  "payment_method": "ONLINE",
  "provider": "RAZORPAY"
}

response:
```json
{
  "success": true,
  "message": "Order created successfully. Online payment is required to complete payment.",
  "order": {
    "id": 15,
    "order_number": "ORD-20261023-9931",
    "total_amount": 1499.0,
    "payment_method": "ONLINE",
    "payment_status": "PENDING",
    "status": "PENDING"
  },
  "payment": {
    "id": 6,
    "reference": "PAY-20261023-72B2B30883",
    "method": "ONLINE",
    "amount": 1499.0,
    "currency": "INR",
    "status": "INITIATED",
    "requires_online_payment": true,
    "provider": "RAZORPAY"
  },
  "payment_instructions": {
    "action_required": true,
    "type": "ONLINE",
    "message": "Please complete online payment with your preferred gateway using the payment reference.",
    "verify_url": "/api/user/payment/verify/"
  },
  "delivery_address": {
    "id": 1,
    "full_name": "Ananya Iyer"
  },
  "cart_cleared": true
}
```


API for Verifying Online Payment
url: http://192.168.1.52:8000/api/user/payment/verify/
method: POST

headers:
Authorization: Bearer <customer_token>
Content-Type: application/json
X-Payment-Signature: <gateway/server generated HMAC-SHA256 signature>

params (success):
{
  "payment_reference": "PAY-20261023-72B2B30883",
  "status": "PAID",
  "provider": "RAZORPAY",
  "provider_payment_id": "pay_O7s6d5f4g3h2j1",
  "provider_order_id": "order_K8j7h6g5f4d3s2"
}

Security requirement:
The verification endpoint does not trust a customer-supplied PAID value by
itself. Configure PAYMENT_WEBHOOK_SECRET on the server and generate
X-Payment-Signature as HMAC-SHA256 over:

payment_reference|status|provider|provider_order_id|provider_payment_id

The payment gateway or trusted backend must create this signature. Never put
PAYMENT_WEBHOOK_SECRET in the mobile app or browser frontend.

response (payment success):
```json
{
  "success": true,
  "message": "Payment verified successfully. Order confirmed.",
  "payment": {
    "id": 6,
    "reference": "PAY-20261023-72B2B30883",
    "order_id": 15,
    "order_number": "ORD-20261023-9931",
    "method": "ONLINE",
    "amount": 1499.0,
    "currency": "INR",
    "status": "PAID",
    "requires_online_payment": false,
    "provider": "RAZORPAY",
    "provider_order_id": "order_K8j7h6g5f4d3s2",
    "provider_payment_id": "pay_O7s6d5f4g3h2j1",
    "paid_at": "2026-10-23T14:52:10+00:00"
  },
  "order": {
    "id": 15,
    "order_number": "ORD-20261023-9931",
    "total_amount": 1499.0,
    "payment_method": "ONLINE",
    "payment_status": "PAID",
    "status": "PENDING"
  }
}
```

params (failed payment):
{
  "payment_reference": "PAY-20261023-72B2B30883",
  "status": "FAILED",
  "provider": "RAZORPAY"
}

response (payment failed):
```json
{
  "success": true,
  "message": "Payment recorded as failed.",
  "payment": {
    "reference": "PAY-20261023-72B2B30883",
    "status": "FAILED"
  },
  "order": {
    "order_number": "ORD-20261023-9931",
    "payment_status": "FAILED"
  }
}
```


API for Checking Payment Status
url: http://192.168.1.52:8000/api/user/payment/status/<payment_reference>/
method: GET

headers:
Authorization: Bearer <customer_token>

response:
```json
{
  "success": true,
  "payment": {
    "reference": "PAY-20261023-72B2B30883",
    "method": "ONLINE",
    "amount": 1499.0,
    "status": "PAID",
    "paid_at": "2026-10-23T14:52:10+00:00"
  },
  "order": {
    "order_number": "ORD-20261023-9931",
    "payment_status": "PAID",
    "status": "PENDING"
  }
}
```


API for Listing Customer Orders
url: http://192.168.1.52:8000/api/user/orders/
method: GET

headers:
Authorization: Bearer <customer_token>

response:
```json
{
  "success": true,
  "count": 2,
  "orders": [
    {
      "id": 15,
      "order_number": "ORD-20261023-9931",
      "total_amount": 1499.0,
      "payment_method": "ONLINE",
      "payment_status": "PAID",
      "status": "PENDING",
      "status_display": "Pending Confirmation",
      "item_count": 1,
      "created_at": "2026-10-23T14:50:00+00:00"
    },
    {
      "id": 14,
      "order_number": "ORD-20261023-4542",
      "total_amount": 49997.0,
      "payment_method": "COD",
      "payment_status": "PENDING",
      "status": "PENDING",
      "status_display": "Pending Confirmation",
      "item_count": 2,
      "created_at": "2026-10-23T14:48:00+00:00"
    }
  ]
}
```


API for Order Details and Status Timeline
url: http://192.168.1.52:8000/api/user/orders/<order_id>/
method: GET

headers:
Authorization: Bearer <customer_token>

response:
```json
{
  "success": true,
  "order": {
    "id": 15,
    "order_number": "ORD-20261023-9931",
    "customer": {
      "full_name": "Ananya Iyer",
      "phone": "9876543211"
    },
    "shipping_address": "12, MG Road, Apartment 4B",
    "shipping_city": "Bengaluru",
    "shipping_state": "Karnataka",
    "shipping_pincode": "560001",
    "total_amount": 1499.0,
    "payment_method": "ONLINE",
    "payment_status": "PAID",
    "status": "PENDING",
    "items": [
      {
        "id": 24,
        "product_name": "65W Fast GaN Charger",
        "price": 1499.0,
        "quantity": 1,
        "total_price": 1499.0
      }
    ],
    "timeline": [
      {
        "old_status": "PENDING",
        "new_status": "PENDING",
        "notes": "Online payment verified successfully via RAZORPAY (pay_O7s6d5f4g3h2j1).",
        "created_at": "2026-10-23T14:52:10+00:00"
      },
      {
        "old_status": "",
        "new_status": "PENDING",
        "notes": "Order item created from customer checkout.",
        "created_at": "2026-10-23T14:50:00+00:00"
      }
    ]
  }
}
```


API for Viewing Cart
url: http://192.168.1.52:8000/api/user/cart/
method: GET

headers:
Authorization: Bearer <customer_token>

response:
```json
{
  "success": true,
  "cart": {
    "item_count": 2,
    "total_quantity": 3,
    "regular_subtotal": 53997.0,
    "discount": 4000.0,
    "total": 49997.0,
    "items": [
      {
        "id": 1,
        "product_id": 81,
        "product_name": "Flagship Smartphone Pro",
        "variant_id": 16,
        "variant_title": "Space Black 256GB",
        "effective_price": 46999.0,
        "quantity": 1,
        "line_total": 46999.0
      }
    ]
  }
}
```


API for Removing Item from Cart
url: http://192.168.1.52:8000/api/user/cart/remove/
method: POST

headers:
Authorization: Bearer <customer_token>
Content-Type: application/json

params:
{
  "cart_item_id": 1
}

response:
```json
{
  "success": true,
  "message": "Item removed from cart successfully.",
  "cart": {
    "item_count": 1,
    "total_quantity": 2,
    "total": 2998.0,
    "items": []
  }
}
```


API for Clearing Cart
url: http://192.168.1.52:8000/api/user/cart/clear/
method: POST

headers:
Authorization: Bearer <customer_token>

response:
```json
{
  "success": true,
  "message": "Cart cleared successfully.",
  "cart": {
    "item_count": 0,
    "total_quantity": 0,
    "total": 0.0,
    "items": []
  }
}
```
