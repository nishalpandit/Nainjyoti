# Checkout, Payment & Order APIs Documentation

This document covers the end-to-end checkout, payment gateway integration (`COD` and `ONLINE`), and order tracking APIs for the customer/mobile app.

---

## 1. Checkout API (Place Order)

Converts the authenticated customer's cart into an atomic order. Validates real-time inventory and variant availability, snapshots the delivery address, creates vendor-specific order items, writes inventory movements to `StockLog`, generates a `PaymentTransaction` record, and clears the cart upon success.

```text
URL: http://192.168.1.52:8000/api/user/checkout/
Method: POST
Authentication: Bearer <customer_token>
Content-Type: application/json
```

### Headers
```text
Authorization: Bearer <customer_token>
Content-Type: application/json
```

### Request Body (COD - Cash on Delivery)
```json
{
  "address_id": 1,
  "payment_method": "COD"
}
```

### Request Body (ONLINE - Online Payment)
```json
{
  "address_id": 1,
  "payment_method": "ONLINE",
  "provider": "RAZORPAY"
}
```
* `address_id` (integer, required): ID of the saved customer address.
* `payment_method` (string, required): Either `"COD"` or `"ONLINE"` (aliases: `"CASH_ON_DELIVERY"`, `"ONLINE_PAYMENT"`, `"PREPAID"`).
* `provider` (string, optional for online): Payment gateway name (e.g. `"RAZORPAY"`, `"STRIPE"`, `"PAYTM"`, `"UPI"`). Defaults to `"ONLINE"`.

### Success Response (COD) — HTTP 201
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
    "payment": {
      "id": 5,
      "reference": "PAY-20261023-A89F0E12",
      "method": "COD",
      "amount": 49997.0,
      "currency": "INR",
      "status": "PENDING",
      "requires_online_payment": false,
      "provider": "COD",
      "provider_order_id": null,
      "provider_payment_id": null,
      "paid_at": null,
      "created_at": "2026-10-23T14:50:00+00:00"
    },
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
  "payment_instructions": {
    "action_required": false,
    "type": "COD",
    "message": "Cash on delivery: pay upon parcel arrival.",
    "verify_url": null
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

### Success Response (ONLINE) — HTTP 201
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

### Error Responses
* **Cart is empty** (HTTP 400):
  ```json
  {"success": false, "message": "Your cart is empty. Add at least one item before checkout."}
  ```
* **Address not found** (HTTP 404):
  ```json
  {"success": false, "message": "Address with ID '99' was not found for this customer."}
  ```
* **Insufficient stock** (HTTP 400):
  ```json
  {
    "success": false,
    "message": "Only 1 item(s) of 'Flagship Smartphone Pro' are available.",
    "cart_item_id": 12,
    "available_stock": 1,
    "requested_quantity": 3
  }
  ```

---

## 2. Online Payment Verification API

Used by frontend/mobile apps after the payment gateway completes. Atomically updates the `PaymentTransaction` and `Order` status, records gateway reference IDs, and logs to `OrderStatusHistory`.

```text
URL: http://192.168.1.52:8000/api/user/payment/verify/
Method: POST
Authentication: Bearer <customer_token>
Content-Type: application/json
```

### Headers
```text
Authorization: Bearer <customer_token>
Content-Type: application/json
```

### Request Body (Payment Success)
```json
{
  "payment_reference": "PAY-20261023-72B2B30883",
  "status": "PAID",
  "provider": "RAZORPAY",
  "provider_payment_id": "pay_O7s6d5f4g3h2j1",
  "provider_order_id": "order_K8j7h6g5f4d3s2"
}
```
*Note: You can pass either `payment_reference`, `order_id`, or `order_number` to identify the transaction.*

### Request Body (Payment Failed)
```json
{
  "payment_reference": "PAY-20261023-72B2B30883",
  "status": "FAILED",
  "provider": "RAZORPAY"
}
```

### Success Response (Payment Verified) — HTTP 200
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

---

## 3. Payment Status Lookup API

Check the status of any payment transaction by its reference code or order number.

```text
URL: http://192.168.1.52:8000/api/user/payment/status/<payment_reference>/
Method: GET
Authentication: Bearer <customer_token>
```

### Success Response — HTTP 200
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

---

## 4. Cart APIs

### View Cart
```text
URL: http://192.168.1.52:8000/api/user/cart/
Method: GET
Authentication: Bearer <customer_token>
```

**Response (HTTP 200):**
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

### Remove Item from Cart
```text
URL: http://192.168.1.52:8000/api/user/cart/remove/
Method: POST
Authentication: Bearer <customer_token>
Content-Type: application/json

Body:
{
  "cart_item_id": 1
}
// OR
{
  "product_id": 81,
  "variant_id": 16
}
```

### Clear Entire Cart
```text
URL: http://192.168.1.52:8000/api/user/cart/clear/
Method: POST
Authentication: Bearer <customer_token>
```

---

## 5. Customer Orders API

### List Customer Orders
```text
URL: http://192.168.1.52:8000/api/user/orders/
Method: GET
Authentication: Bearer <customer_token>
```
*Optional Query Param:* `?status=PENDING` / `CONFIRMED` / `SHIPPED` / `DELIVERED`

**Response (HTTP 200):**
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
    }
  ]
}
```

### Get Order Detail with Timeline
```text
URL: http://192.168.1.52:8000/api/user/orders/<order_id>/
Method: GET
Authentication: Bearer <customer_token>
```

**Response (HTTP 200):**
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
