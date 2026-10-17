API for Inventory Stock Summary  
url: http://192.168.1.52:8000/api/vendor/stock/summary/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory for multi-tenant vendor scoping)  

params:  
none  

response:  
```json
{
  "success": true,
  "summary": {
    "total_skus": 4,
    "total_units": 122,
    "healthy_count": 3,
    "low_stock_count": 0,
    "out_of_stock_count": 1,
    "total_valuation": 324278.0,
    "currency": "INR"
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

---

API for Inventory Stock List  
url: http://192.168.1.52:8000/api/vendor/stock/list/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory to scope inventory to authenticated vendor)  

params:  
level: low_stock (optional, choices: all, low_stock, out_of_stock, healthy)  
category_id: 2 (optional, filter by Category master ID)  
search: Plate (optional, search by product name or SKU)  
ordering: -stock_quantity (optional, choices: -stock_quantity, stock_quantity, -price, price)  

response:  
```json
{
  "success": true,
  "count": 1,
  "inventory": [
    {
      "product_id": 6,
      "name": "Jaipur Handcrafted Ceramic Dinner Plate",
      "sku": "STOCK-TEST-1234AB",
      "category_id": 2,
      "category_name": "Electronics & Appliances",
      "vendor_id": 7,
      "vendor_name": "Kashmir Pashmina & Crafts",
      "price": 499.0,
      "stock_quantity": 8,
      "low_stock_threshold": 10,
      "stock_status": "LOW_STOCK",
      "stock_valuation": 3992.0,
      "unit": "Piece",
      "image": null,
      "last_updated": "2026-10-17T07:11:16.890123+00:00"
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

API for Adjust Inventory Stock  
url: http://192.168.1.52:8000/api/vendor/stock/update/6/  
method: POST  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory to verify store ownership)  

params:  
action: ADD (required, choices: ADD, SUBTRACT, SET)  
quantity: 20 (required, units to add/subtract or target count)  
movement_type: RESTOCK (optional, choices: RESTOCK, SALE, RETURN, DAMAGE, CORRECTION)  
reason: Received batch invoice #REC-8841 from supplier (optional)  
reference_id: PO-8841 (optional, purchase order / batch / receipt number)  
low_stock_threshold: 10 (optional, update reorder alert threshold)  

response:  
```json
{
  "success": true,
  "message": "Stock for 'Jaipur Handcrafted Ceramic Dinner Plate' adjusted from 30 to 50 units.",
  "product": {
    "id": 6,
    "vendor_id": 7,
    "vendor_name": "Kashmir Pashmina & Crafts",
    "name": "Jaipur Handcrafted Ceramic Dinner Plate",
    "sku": "STOCK-TEST-1234AB",
    "price": 499.0,
    "stock_quantity": 50,
    "low_stock_threshold": 10,
    "stock_status": "HEALTHY",
    "stock_valuation": 24950.0,
    "status": "ACTIVE"
  },
  "log": {
    "id": 1,
    "product_id": 6,
    "product_name": "Jaipur Handcrafted Ceramic Dinner Plate",
    "sku": "STOCK-TEST-1234AB",
    "vendor_id": 7,
    "movement_type": "RESTOCK",
    "movement_type_display": "Restock / Purchase",
    "quantity_changed": 20,
    "previous_stock": 30,
    "new_stock": 50,
    "reason": "Received batch invoice #REC-8841 from supplier",
    "reference_id": "PO-8841",
    "created_at": "2026-10-17T07:11:16.920456+00:00"
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
  "message": "Access denied. You do not have permission to adjust stock for this product."
}
```

---

API for Stock Movement Audit Logs  
url: http://192.168.1.52:8000/api/vendor/stock/logs/6/  
method: GET  

headers:  
Authorization: Bearer <vendor_token> (required - strictly mandatory for audit ledger access)  

params:  
movement_type: RESTOCK (optional, filter by RESTOCK, SALE, RETURN, DAMAGE, CORRECTION)  
limit: 50 (optional, default: 50)  

response:  
```json
{
  "success": true,
  "count": 2,
  "logs": [
    {
      "id": 2,
      "product_id": 6,
      "product_name": "Jaipur Handcrafted Ceramic Dinner Plate",
      "sku": "STOCK-TEST-1234AB",
      "vendor_id": 7,
      "movement_type": "DAMAGE",
      "movement_type_display": "Damaged / Expired / Lost",
      "quantity_changed": -5,
      "previous_stock": 50,
      "new_stock": 45,
      "reason": "Broken during warehouse transit",
      "reference_id": "DMG-102",
      "created_at": "2026-10-17T07:11:16.950123+00:00"
    },
    {
      "id": 1,
      "product_id": 6,
      "product_name": "Jaipur Handcrafted Ceramic Dinner Plate",
      "sku": "STOCK-TEST-1234AB",
      "vendor_id": 7,
      "movement_type": "RESTOCK",
      "movement_type_display": "Restock / Purchase",
      "quantity_changed": 20,
      "previous_stock": 30,
      "new_stock": 50,
      "reason": "Received batch invoice #REC-8841 from supplier",
      "reference_id": "PO-8841",
      "created_at": "2026-10-17T07:11:16.920456+00:00"
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

forbidden_error_response (403):  
```json
{
  "success": false,
  "message": "Access denied. You do not have permission to view stock logs for this product."
}
```
