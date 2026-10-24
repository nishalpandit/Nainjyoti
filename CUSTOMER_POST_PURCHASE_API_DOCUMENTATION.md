# Customer Post-Purchase APIs

Authenticated endpoints require:

```text
Authorization: Bearer <customer_token>
```
*(Note: Bearer tokens are permanent and never expire).*

## Order tracking

```text
url: http://192.168.1.52:8000/api/user/orders/<order_id>/tracking/
method: GET
params: No body params
```

Returns the overall order/payment status, item-level status, courier name,
tracking number, dispatch/delivery timestamps, and status timeline.

## Create cancellation or return request

```text
url: http://192.168.1.52:8000/api/user/orders/<order_id>/request/
method: POST
content-type: application/json
```

Cancellation params:

```json
{
  "request_type": "CANCEL",
  "order_item_id": 58,
  "reason": "Ordered by mistake",
  "details": "Please cancel before dispatch."
}
```

Return params:

```json
{
  "request_type": "RETURN",
  "order_item_id": 59,
  "reason": "Item arrived damaged",
  "details": "The package was damaged on arrival."
}
```

`order_item_id` is optional when the request applies to the complete order.
Cancellation is accepted only for `PENDING`, `CONFIRMED`, or `PROCESSING`
items/orders. Returns are accepted only after `DELIVERED`.

Response:

```json
{
  "success": true,
  "message": "Return request submitted successfully.",
  "request": {
    "id": 2,
    "request_number": "REQ-20261023-9919FC49",
    "request_type": "RETURN",
    "order_id": 47,
    "order_item_id": 59,
    "reason": "Item arrived damaged",
    "status": "PENDING"
  }
}
```

List the customer's requests:

```text
url: http://192.168.1.52:8000/api/user/order-requests/
method: GET
optional query params: request_type=CANCEL|RETURN, status=PENDING|APPROVED|REJECTED|COMPLETED
```

## Ratings and reviews

List approved reviews (public):

```text
url: http://192.168.1.52:8000/api/user/products/<product_id>/reviews/
method: GET
```

Create a review (customer token required):

```text
url: http://192.168.1.52:8000/api/user/products/<product_id>/reviews/
method: POST
```

```json
{
  "variant_id": 16,
  "rating": 5,
  "title": "Excellent quality",
  "comment": "The black variant looks and works great."
}
```

Update a customer-owned review:

```text
url: http://192.168.1.52:8000/api/user/reviews/<review_id>/update/
method: PATCH
```

Delete a customer-owned review:

```text
url: http://192.168.1.52:8000/api/user/reviews/<review_id>/delete/
method: DELETE
```

Only one review per customer/product is allowed. The response includes
`is_verified_purchase`, which is true when a matching delivered order exists.

## Notifications

List notifications:

```text
url: http://192.168.1.52:8000/api/user/notifications/
method: GET
query params: status=all|read|unread, type=ORDER|PAYMENT|CANCELLATION|RETURN|PROMOTION|SYSTEM, page=1, limit=20
```

Get unread badge count:

```text
url: http://192.168.1.52:8000/api/user/notifications/unread-count/
method: GET
```

Mark one notification as read:

```text
url: http://192.168.1.52:8000/api/user/notifications/<notification_id>/read/
method: POST
```

Mark every notification as read:

```text
url: http://192.168.1.52:8000/api/user/notifications/read-all/
method: POST
```

Notifications are automatically created for checkout/order placement, online
payment status changes, and cancellation/return request submission.

## Live verification record

Verified on 2026-10-23 using customer ID `24`, product ID `81`, and variant ID
`16`. The audit created one COD cancellation request, one delivered-item return
request, one review, five notifications, and three orders (COD, ONLINE, COD).
All related records and stock-sale logs were confirmed directly in the database.
