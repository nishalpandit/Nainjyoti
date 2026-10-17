import urllib.request
import urllib.parse
import urllib.error
import json
import uuid
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()
from django.contrib.auth.models import User
from nainjyoti.models import (
    VendorProfile, UserProfile, Category, Product, Order, OrderItem,
    OrderStatusHistory, VendorEarning, VendorPayout
)

BASE_URL = "http://127.0.0.1:8000"

def send_request(method, path, data=None, headers=None):
    url = f"{BASE_URL}{path}"
    headers = headers or {}
    body = None

    if data is not None:
        if isinstance(data, dict):
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            if headers.get("Content-Type") == "application/json":
                body = json.dumps(data).encode("utf-8")
            else:
                body = urllib.parse.urlencode(data).encode("utf-8")
        elif isinstance(data, (bytes, bytearray)):
            body = data

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            res_body = resp.read().decode("utf-8")
            try:
                return status, json.loads(res_body)
            except Exception:
                return status, res_body
    except urllib.error.HTTPError as e:
        status = e.code
        res_body = e.read().decode("utf-8")
        try:
            return status, json.loads(res_body)
        except Exception:
            return status, res_body

def setup_test_data():
    # Vendor A (merchant@crafts.in)
    u_a, _ = User.objects.get_or_create(username='merchant@crafts.in', defaults={'email': 'merchant@crafts.in'})
    u_a.set_password('SellerSecure@2026')
    u_a.save()
    v_a, _ = VendorProfile.objects.get_or_create(user=u_a, defaults={
        'business_name': 'Kashmir Pashmina & Crafts',
        'owner_name': 'Tariq Butt',
        'phone': '9876543210',
        'bank_name': 'HDFC Bank',
        'account_number': '50100492817291',
        'ifsc_code': 'HDFC0000123',
        'status': 'APPROVED'
    })
    v_a.status = 'APPROVED'
    v_a.bank_name = v_a.bank_name or 'HDFC Bank'
    v_a.account_number = v_a.account_number or '50100492817291'
    v_a.ifsc_code = v_a.ifsc_code or 'HDFC0000123'
    if not v_a.auth_token:
        v_a.auth_token = '589031eb3c3b5a16bd354e88aa884e9611a827b9145f08c3d1beb090c8674584'
    v_a.save()

    # Vendor B
    u_b, _ = User.objects.get_or_create(username='vendor_b@nainjyoti.com', defaults={'email': 'vendor_b@nainjyoti.com'})
    v_b, _ = VendorProfile.objects.get_or_create(user=u_b, defaults={
        'business_name': 'Jaipur Blue Pottery Store',
        'owner_name': 'Rajesh Sharma',
        'phone': '9876543299',
        'bank_name': 'ICICI Bank',
        'account_number': '001105001234',
        'ifsc_code': 'ICIC0000011',
        'status': 'APPROVED'
    })
    v_b.status = 'APPROVED'
    v_b.bank_name = v_b.bank_name or 'ICICI Bank'
    v_b.account_number = v_b.account_number or '001105001234'
    v_b.ifsc_code = v_b.ifsc_code or 'ICIC0000011'
    if not v_b.auth_token:
        v_b.generate_new_token()
    v_b.save()

    # Category
    cat, _ = Category.objects.get_or_create(name='Accessories & Crafts', defaults={'status': 'ACTIVE'})

    # Product A
    prod_a, _ = Product.objects.get_or_create(
        sku='PASHMINA-TEST-001',
        defaults={
            'vendor': v_a,
            'category': cat,
            'name': 'Pure Pashmina Shawl Handwoven',
            'price': 4999.00,
            'stock_quantity': 25,
            'status': 'ACTIVE'
        }
    )

    # Product B
    prod_b, _ = Product.objects.get_or_create(
        sku='POTTERY-TEST-001',
        defaults={
            'vendor': v_b,
            'category': cat,
            'name': 'Handmade Blue Ceramic Vase',
            'price': 1299.00,
            'stock_quantity': 40,
            'status': 'ACTIVE'
        }
    )

    # Create a realistic test Order containing Product A for Vendor A
    order = Order.objects.create(
        customer_name='Ananya Verma',
        customer_phone='9876543210',
        customer_email='ananya@example.com',
        shipping_address='Flat 402, Lotus Greens, Sector 78',
        shipping_city='Noida',
        shipping_state='Uttar Pradesh',
        shipping_pincode='201301',
        total_amount=4999.00,
        payment_method='PREPAID',
        payment_status='PAID',
        status='PROCESSING'
    )

    item_a = OrderItem.objects.create(
        order=order,
        vendor=v_a,
        product=prod_a,
        product_name=prod_a.name,
        product_sku=prod_a.sku,
        price=prod_a.price,
        quantity=1,
        total_price=prod_a.price,
        status='PROCESSING'
    )

    OrderStatusHistory.objects.create(
        order=order,
        order_item=item_a,
        vendor=v_a,
        old_status='PENDING',
        new_status='PROCESSING',
        notes='Order accepted and being packaged for courier handover'
    )

    return v_a, v_b, order

def run_tests():
    print("=" * 65)
    print(" STARTING VENDOR ORDERS, STATUS, SALES & EARNINGS TEST SUITE ")
    print("=" * 65)

    vendor_a, vendor_b, order = setup_test_data()
    headers_a = {"Authorization": f"Bearer {vendor_a.auth_token}"}
    headers_b = {"Authorization": f"Bearer {vendor_b.auth_token}"}

    # 1. Test unauthenticated call to /api/vendor/orders/ -> 401
    print("\n[1] Testing Security: Unauthenticated GET /api/vendor/orders/...")
    st_no_auth, resp_no_auth = send_request("GET", "/api/vendor/orders/")
    print(f" -> Status: {st_no_auth}, Message: {resp_no_auth.get('message')}")
    assert st_no_auth == 401
    assert resp_no_auth.get("success") is False

    # 2. Test authenticated GET /api/vendor/orders/ for Vendor A
    print("\n[2] Testing GET /api/vendor/orders/ with Vendor A token...")
    st_orders_a, resp_orders_a = send_request("GET", "/api/vendor/orders/", headers=headers_a)
    print(f" -> Status: {st_orders_a}, Count: {resp_orders_a.get('count')}")
    assert st_orders_a == 200
    assert resp_orders_a.get("count") >= 1
    ord_first = resp_orders_a["orders"][0]
    assert ord_first["order_number"] == order.order_number
    assert ord_first["customer_name"] == "Ananya Verma"
    assert len(ord_first["items"]) == 1
    print(f" -> Verified Order: {ord_first['order_number']}, Subtotal: Rs.{ord_first['vendor_subtotal']}")

    # 3. Test multi-tenant isolation: Vendor B does not see Vendor A's order
    print("\n[3] Testing Multi-Tenant Scoping: Vendor B GET /api/vendor/orders/...")
    st_orders_b, resp_orders_b = send_request("GET", "/api/vendor/orders/", headers=headers_b)
    assert st_orders_b == 200
    b_order_ids = [o["id"] for o in resp_orders_b.get("orders", [])]
    assert order.id not in b_order_ids, "Vendor A's order leaked to Vendor B!"
    print(f" -> Vendor B sees {len(b_order_ids)} orders (ZERO orders of Vendor A leaked!)")

    # 4. Test Customer and Order Details API for Vendor A
    print(f"\n[4] Testing GET /api/vendor/orders/{order.id}/ by Vendor A...")
    st_det, resp_det = send_request("GET", f"/api/vendor/orders/{order.id}/", headers=headers_a)
    assert st_det == 200
    ord_det = resp_det["order"]
    assert ord_det["order_number"] == order.order_number
    assert ord_det["customer"]["name"] == "Ananya Verma"
    assert ord_det["shipping_address"]["city"] == "Noida"
    assert len(ord_det["status_history"]) >= 1
    print(f" -> Order Detail verified! Customer: {ord_det['customer']['name']} ({ord_det['customer']['phone']})")

    # 5. Test Multi-tenant Security: Vendor B attempts to view Vendor A's order -> 403 Forbidden!
    print(f"\n[5] Testing Security: Vendor B attempts to view Vendor A's order ({order.id})...")
    st_cross_det, resp_cross_det = send_request("GET", f"/api/vendor/orders/{order.id}/", headers=headers_b)
    print(f" -> Status: {st_cross_det}, Response: {resp_cross_det}")
    assert st_cross_det == 403
    assert "Access denied" in resp_cross_det.get("message", "")
    print(" -> PASSED: Vendor B is forbidden from viewing Vendor A's customer/order details!")

    # 6. Test Order Status Update: SHIPPED with Tracking info
    print(f"\n[6] Testing POST /api/vendor/orders/{order.id}/status/ (SHIPPED)...")
    ship_payload = {
        "status": "SHIPPED",
        "courier_name": "BlueDart Express",
        "tracking_number": "BD-8849102",
        "notes": "Package dispatched via Air Express"
    }
    st_ship, resp_ship = send_request("POST", f"/api/vendor/orders/{order.id}/status/", data=ship_payload, headers=headers_a)
    assert st_ship == 200
    assert resp_ship["new_status"] == "SHIPPED"
    assert resp_ship["tracking_info"]["courier_name"] == "BlueDart Express"
    print(f" -> Order successfully marked SHIPPED with Tracking {resp_ship['tracking_info']['tracking_number']}")

    # 7. Test Order Status Update: DELIVERED (triggers automatic earnings clearance)
    print(f"\n[7] Testing POST /api/vendor/orders/{order.id}/status/ (DELIVERED)...")
    deliver_payload = {
        "status": "DELIVERED",
        "notes": "Delivered to customer doorstep and verified"
    }
    st_deliv, resp_deliv = send_request("POST", f"/api/vendor/orders/{order.id}/status/", data=deliver_payload, headers=headers_a)
    assert st_deliv == 200
    assert resp_deliv["new_status"] == "DELIVERED"
    print(f" -> Order successfully marked DELIVERED!")

    # 8. Test Sales Overview API
    print("\n[8] Testing GET /api/vendor/sales/overview/...")
    st_sales, resp_sales = send_request("GET", "/api/vendor/sales/overview/", headers=headers_a)
    assert st_sales == 200
    kpis = resp_sales["kpis"]
    assert kpis["total_orders"] >= 1
    assert kpis["total_revenue"] >= 4999.00
    assert kpis["delivered_orders"] >= 1
    print(f" -> Sales KPIs: Revenue=Rs.{kpis['total_revenue']}, Orders={kpis['total_orders']}, Delivered={kpis['delivered_orders']}")

    # 9. Test Earnings Overview API
    print("\n[9] Testing GET /api/vendor/earnings/overview/...")
    st_earn, resp_earn = send_request("GET", "/api/vendor/earnings/overview/", headers=headers_a)
    assert st_earn == 200
    bal = resp_earn["balance_summary"]
    assert bal["lifetime_gross_sales"] >= 4999.00
    assert bal["available_balance"] > 0
    print(f" -> Earnings Summary: Gross=Rs.{bal['lifetime_gross_sales']}, Net=Rs.{bal['lifetime_net_earnings']}, Available=Rs.{bal['available_balance']}")

    # 10. Test Payout Request: Exceeding Available Balance -> 400 Bad Request
    print("\n[10] Testing Security: Payout request exceeding available balance...")
    bad_payout_payload = {"amount": 9999999.00}
    st_bad_payout, resp_bad_payout = send_request("POST", "/api/vendor/payout/request/", data=bad_payout_payload, headers=headers_a)
    assert st_bad_payout == 400
    msg_clean = resp_bad_payout['message'].replace('₹', 'Rs.')
    print(f" -> PASSED: Excess withdrawal rejected: {msg_clean}")

    # 11. Test Valid Payout Request
    print("\n[11] Testing POST /api/vendor/payout/request/ with valid amount (Rs. 1000)...")
    valid_payout_payload = {
        "amount": 1000.00,
        "notes": "Weekly seller payout test"
    }
    st_payout, resp_payout = send_request("POST", "/api/vendor/payout/request/", data=valid_payout_payload, headers=headers_a)
    assert st_payout == 201
    payout_id = resp_payout["payout"]["id"]
    payout_num = resp_payout["payout"]["payout_number"]
    print(f" -> Payout #{payout_num} requested successfully! Remaining balance: Rs.{resp_payout['remaining_available_balance']}")

    # 12. Test Payout History API
    print("\n[12] Testing GET /api/vendor/payout/history/...")
    st_hist, resp_hist = send_request("GET", "/api/vendor/payout/history/", headers=headers_a)
    assert st_hist == 200
    assert resp_hist["count"] >= 1
    print(f" -> Payout History: {resp_hist['count']} requests found.")

    # 13. Test Settlement Details API
    print(f"\n[13] Testing GET /api/vendor/payout/detail/{payout_id}/...")
    st_pdet, resp_pdet = send_request("GET", f"/api/vendor/payout/detail/{payout_id}/", headers=headers_a)
    assert st_pdet == 200
    assert resp_pdet["payout"]["id"] == payout_id
    assert resp_pdet["payout"]["amount"] == 1000.00
    print(f" -> Payout Detail verified! Amount: Rs.{resp_pdet['payout']['amount']}, Bank: {resp_pdet['payout']['bank_name']}")

    # 14. Test Multi-tenant Security: Vendor B cannot view Vendor A's payout -> 403
    print(f"\n[14] Testing Security: Vendor B attempts to view Vendor A's payout ({payout_id})...")
    st_cross_p, resp_cross_p = send_request("GET", f"/api/vendor/payout/detail/{payout_id}/", headers=headers_b)
    assert st_cross_p == 403
    print(" -> PASSED: Vendor B is forbidden from inspecting Vendor A's payout details!")

    print("\n" + "=" * 65)
    print(" ALL 14 ORDER, SALES, EARNINGS & SETTLEMENT TESTS PASSED 100%! ")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
