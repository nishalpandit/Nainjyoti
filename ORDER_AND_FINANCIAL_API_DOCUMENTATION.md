API for Vendor Orders List  
url: http://192.168.1.52:8000/api/vendor/orders/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory to scope orders to authenticated vendor)  

params:  
status: PROCESSING (optional, choices: ALL, PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED, RETURNED)  
search: ORD-20261017 (optional, search by order number, customer name, or phone number)  
date_from: 2026-10-01 (optional, YYYY-MM-DD start date filter)  
date_to: 2026-10-17 (optional, YYYY-MM-DD end date filter)  
ordering: -created_at (optional, choices: -created_at, created_at, -total_amount, total_amount)  
limit: 50 (optional, default: 50, max: 200)  

response:  
```json
{
  "success": true,
  "count": 1,
  "orders": [
    {
      "id": 1,
      "order_number": "ORD-20261017-1001",
      "customer_name": "Ananya Verma",
      "customer_phone": "9876543210",
      "customer_email": "ananya@example.com",
      "shipping_address": "Flat 402, Lotus Greens, Sector 78",
      "shipping_city": "Noida",
      "shipping_state": "Uttar Pradesh",
      "shipping_pincode": "201301",
      "total_amount": 3499.0,
      "vendor_subtotal": 3499.0,
      "payment_method": "PREPAID",
      "payment_status": "PAID",
      "status": "PROCESSING",
      "status_display": "Processing",
      "item_count": 1,
      "items": [
        {
          "id": 1,
          "order_id": 1,
          "order_number": "ORD-20261017-1001",
          "product_id": 10,
          "product_name": "Wireless Noise Cancelling Smart Watch Pro",
          "product_sku": "WATCH-5A6F35",
          "price": 3499.0,
          "quantity": 1,
          "total_price": 3499.0,
          "status": "PROCESSING",
          "status_display": "Processing",
          "courier_name": "",
          "tracking_number": "",
          "dispatch_date": null,
          "delivery_date": null,
          "created_at": "2026-10-17T07:54:03.381703+00:00"
        }
      ],
      "created_at": "2026-10-17T07:54:03.381703+00:00",
      "updated_at": "2026-10-17T07:54:03.381738+00:00"
    }
  ]
}
```

unauthorized_error_response (401):  
```json
{
  "success": false,
  "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
}
```

---

API for Customer & Order Details  
url: http://192.168.1.52:8000/api/vendor/orders/1/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory to verify vendor store ownership)  

params:  
none  

response:  
```json
{
  "success": true,
  "order": {
    "id": 1,
    "order_number": "ORD-20261017-1001",
    "customer": {
      "name": "Ananya Verma",
      "phone": "9876543210",
      "email": "ananya@example.com"
    },
    "shipping_address": {
      "address": "Flat 402, Lotus Greens, Sector 78",
      "city": "Noida",
      "state": "Uttar Pradesh",
      "pincode": "201301"
    },
    "payment": {
      "method": "PREPAID",
      "status": "PAID"
    },
    "status": "PROCESSING",
    "status_display": "Processing",
    "vendor_subtotal": 3499.0,
    "total_amount": 3499.0,
    "items": [
      {
        "id": 1,
        "product_id": 10,
        "product_name": "Wireless Noise Cancelling Smart Watch Pro",
        "product_sku": "WATCH-5A6F35",
        "price": 3499.0,
        "quantity": 1,
        "total_price": 3499.0,
        "status": "PROCESSING",
        "status_display": "Processing",
        "courier_name": "BlueDart Express",
        "tracking_number": "BD-98213490",
        "dispatch_date": null,
        "delivery_date": null
      }
    ],
    "status_history": [
      {
        "old_status": "CONFIRMED",
        "new_status": "PROCESSING",
        "notes": "Packed and ready for pickup by courier",
        "created_at": "2026-10-17T08:15:00.000000+00:00"
      },
      {
        "old_status": "PENDING",
        "new_status": "CONFIRMED",
        "notes": "Order confirmed by merchant",
        "created_at": "2026-10-17T07:55:00.000000+00:00"
      }
    ],
    "created_at": "2026-10-17T07:54:03.381703+00:00",
    "updated_at": "2026-10-17T08:15:00.000000+00:00"
  }
}
```

unauthorized_error_response (401):  
```json
{
  "success": false,
  "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
}
```

forbidden_error_response (403):  
```json
{
  "success": false,
  "message": "Access denied. You do not have permission to view this order."
}
```

---

API for Order Status Update  
url: http://192.168.1.52:8000/api/vendor/orders/1/status/  
method: POST  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory)  

params:  
status: SHIPPED (required, choices: CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED)  
courier_name: BlueDart Express (optional, recommended when status is SHIPPED)  
tracking_number: BD-98213490 (optional, recommended when status is SHIPPED)  
notes: Handed over to BlueDart courier hub for priority delivery (optional)  

response:  
```json
{
  "success": true,
  "message": "Order status successfully updated to 'SHIPPED'.",
  "order_id": 1,
  "order_number": "ORD-20261017-1001",
  "previous_status": "PROCESSING",
  "new_status": "SHIPPED",
  "tracking_info": {
    "courier_name": "BlueDart Express",
    "tracking_number": "BD-98213490",
    "dispatch_date": "2026-10-17T08:30:00.000000+00:00"
  }
}
```

unauthorized_error_response (401):  
```json
{
  "success": false,
  "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
}
```

forbidden_error_response (403):  
```json
{
  "success": false,
  "message": "Access denied. You do not have permission to modify this order."
}
```

---

API for Sales Overview  
url: http://192.168.1.52:8000/api/vendor/sales/overview/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory)  

params:  
period: month (optional, choices: today, week, month, year, all, default: month)  

response:  
```json
{
  "success": true,
  "period": "month",
  "kpis": {
    "total_revenue": 184500.0,
    "total_orders": 48,
    "units_sold": 95,
    "average_order_value": 3843.75,
    "delivered_orders": 42,
    "processing_orders": 4,
    "shipped_orders": 2,
    "cancelled_orders": 0,
    "currency": "INR"
  },
  "status_breakdown": {
    "DELIVERED": 42,
    "PROCESSING": 4,
    "SHIPPED": 2,
    "CANCELLED": 0
  },
  "daily_trend": [
    {
      "date": "2026-10-15",
      "orders": 6,
      "revenue": 21500.0
    },
    {
      "date": "2026-10-16",
      "orders": 8,
      "revenue": 29800.0
    },
    {
      "date": "2026-10-17",
      "orders": 4,
      "revenue": 14200.0
    }
  ],
  "top_selling_products": [
    {
      "product_id": 10,
      "name": "Wireless Noise Cancelling Smart Watch Pro",
      "sku": "WATCH-5A6F35",
      "units_sold": 34,
      "revenue": 118966.0
    }
  ]
}
```

unauthorized_error_response (401):  
```json
{
  "success": false,
  "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
}
```

---

API for Earnings Overview  
url: http://192.168.1.52:8000/api/vendor/earnings/overview/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory)  

params:  
none  

response:  
```json
{
  "success": true,
  "balance_summary": {
    "lifetime_gross_sales": 184500.0,
    "platform_commission_rate_percent": 5.0,
    "total_commission_deducted": 9225.0,
    "lifetime_net_earnings": 175275.0,
    "available_balance": 125275.0,
    "pending_clearance": 20000.0,
    "total_withdrawn": 30000.0,
    "currency": "INR"
  },
  "recent_earnings": [
    {
      "id": 1,
      "order_id": 1,
      "order_number": "ORD-20261017-1001",
      "gross_amount": 3499.0,
      "commission_rate": 5.0,
      "commission_amount": 174.95,
      "net_amount": 3324.05,
      "status": "AVAILABLE",
      "status_display": "Available for Withdrawal",
      "cleared_at": "2026-10-17T09:00:00.000000+00:00",
      "created_at": "2026-10-17T07:54:03.381703+00:00"
    }
  ]
}
```

unauthorized_error_response (401):  
```json
{
  "success": false,
  "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
}
```

---

API for Request Withdrawal / Settlement  
url: http://192.168.1.52:8000/api/vendor/payout/request/  
method: POST  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory)  

params:  
amount: 25000.00 (required, must not exceed available_balance)  
bank_name: HDFC Bank (optional, defaults to registered vendor store bank account)  
account_number: 50100492817291 (optional, defaults to registered vendor store bank account)  
ifsc_code: HDFC0000123 (optional, defaults to registered vendor store bank account)  
notes: Weekly store payout request (optional)  

response:  
```json
{
  "success": true,
  "message": "Withdrawal request of ₹25000.00 submitted successfully! Funds will be credited after compliance processing.",
  "payout": {
    "id": 1,
    "payout_number": "PAY-20261017-8419",
    "vendor_id": 7,
    "vendor_name": "Kashmir Pashmina & Crafts",
    "amount": 25000.0,
    "bank_name": "HDFC Bank",
    "account_number": "50100492817291",
    "ifsc_code": "HDFC0000123",
    "status": "PENDING",
    "status_display": "Pending Approval",
    "utr_number": "",
    "requested_at": "2026-10-17T09:30:00.000000+00:00"
  },
  "remaining_available_balance": 100275.0
}
```

unauthorized_error_response (401):  
```json
{
  "success": false,
  "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
}
```

validation_error_response (400):  
```json
{
  "success": false,
  "message": "Requested amount ₹150000.00 exceeds your current available balance of ₹125275.00."
}
```

---

API for Withdrawal / Settlement History  
url: http://192.168.1.52:8000/api/vendor/payout/history/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory)  

params:  
status: COMPLETED (optional, choices: ALL, PENDING, PROCESSING, COMPLETED, REJECTED)  
limit: 50 (optional, default: 50)  

response:  
```json
{
  "success": true,
  "count": 1,
  "payouts": [
    {
      "id": 1,
      "payout_number": "PAY-20261017-8419",
      "vendor_id": 7,
      "vendor_name": "Kashmir Pashmina & Crafts",
      "amount": 25000.0,
      "bank_name": "HDFC Bank",
      "account_number": "50100492817291",
      "ifsc_code": "HDFC0000123",
      "status": "COMPLETED",
      "status_display": "Completed / Settled",
      "utr_number": "UTR982138941038",
      "admin_notes": "NEFT transfer processed successfully",
      "requested_at": "2026-10-17T09:30:00.000000+00:00",
      "processed_at": "2026-10-17T11:00:00.000000+00:00"
    }
  ]
}
```

unauthorized_error_response (401):  
```json
{
  "success": false,
  "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
}
```

---

API for Settlement Details  
url: http://192.168.1.52:8000/api/vendor/payout/detail/1/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory to verify store ownership)  

params:  
none  

response:  
```json
{
  "success": true,
  "payout": {
    "id": 1,
    "payout_number": "PAY-20261017-8419",
    "vendor_id": 7,
    "vendor_name": "Kashmir Pashmina & Crafts",
    "amount": 25000.0,
    "bank_name": "HDFC Bank",
    "account_number": "50100492817291",
    "ifsc_code": "HDFC0000123",
    "status": "COMPLETED",
    "status_display": "Completed / Settled",
    "utr_number": "UTR982138941038",
    "admin_notes": "NEFT transfer processed successfully",
    "requested_at": "2026-10-17T09:30:00.000000+00:00",
    "processed_at": "2026-10-17T11:00:00.000000+00:00"
  }
}
```

unauthorized_error_response (401):  
```json
{
  "success": false,
  "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
}
```

forbidden_error_response (403):  
```json
{
  "success": false,
  "message": "Access denied. You do not have permission to view this settlement."
}
```
