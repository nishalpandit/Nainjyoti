# Customer API Verification Report

Verification date: 2026-10-23

Base URL: `http://192.168.1.52:8000`

Live audit customer: ID `24`, phone `9892751035`

| Feature | Endpoint tested | HTTP result |
|---|---|---:|
| Registration | `POST /api/user/register/` | 201 |
| Login | `POST /api/user/login/` | 200 |
| Profile get/update | `GET /api/user/profile/`, `POST /api/user/profile/update/` | 200 |
| Address create/list/detail/update/default/delete | `/api/user/address/...` | 200/201 |
| Category list/detail/products | `/api/user/categories/...` | 200 |
| Product search | `GET /api/user/products/search/` | 200 |
| Product details | `GET /api/user/products/81/` | 200 |
| Product variants | `GET /api/user/products/81/variants/` | 200 |
| Cart add/list/remove/clear | `/api/user/cart/...` | 200/201 |
| Wishlist add/list/remove exact variant | `/api/user/wishlist/...` | 200/201 |
| Checkout COD | `POST /api/user/checkout/` | 201 |
| Checkout online | `POST /api/user/checkout/` | 201 |
| Payment status | `GET /api/user/payment/status/<reference>/` | 200 |
| Order placement | Checkout-created orders | 201 |
| Order history | `GET /api/user/orders/` | 200 |
| Order detail | `GET /api/user/orders/<id>/` | 200 |
| Order tracking | `GET /api/user/orders/<id>/tracking/` | 200 |
| Cancellation request | `POST /api/user/orders/45/request/` | 201 |
| Return request | `POST /api/user/orders/47/request/` | 201 |
| Request history | `GET /api/user/order-requests/` | 200 |
| Review create/list/update/delete | `/api/user/products/.../reviews/`, `/api/user/reviews/...` | 200/201 |
| Notifications list/count/read/read-all | `/api/user/notifications/...` | 200 |

## Database confirmation

- Customer ID `24` and default address ID `6` were persisted.
- Exact wishlist selection persisted: product `81`, variant `16` (Black).
- COD orders `45` and `47`, and online order `46`, were persisted.
- Online payment reference `PAY-20261023-B5070C3E72` persisted with status
  `INITIATED`.
- Cancellation request and return request persisted with status `PENDING`.
- Product review ID `1` persisted with rating `4`.
- Five notifications persisted and read-state updates were confirmed.
- Three `SALE` stock logs were created and the exact variant inventory was
  reduced for each checkout.
- The audit customer's cart was empty after checkout/clear operations.

## Online payment security

Online checkout and payment-status retrieval are active. Marking an online
payment as paid requires `PAYMENT_WEBHOOK_SECRET` and a valid server/gateway
HMAC signature. No browser or mobile client can mark its own order as paid.
A real charge still requires a selected payment gateway and its credentials.
