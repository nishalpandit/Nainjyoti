import urllib.request
import json

BASE = 'http://127.0.0.1:8000'

# 1. Login with user credentials
login_data = json.dumps({'username': 'merchant@crafts.in', 'password': 'SellerSecure@2026'}).encode('utf-8')
req = urllib.request.Request(f'{BASE}/api/vendor/login/', data=login_data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as r:
    login_resp = json.loads(r.read().decode('utf-8'))
    print("LOGIN SUCCESS:", login_resp.get('success'))
    print("STORE NAME:", login_resp.get('vendor', {}).get('business_name'))
    token = login_resp.get('token')
    print("TOKEN:", token)

headers = {'Authorization': f'Bearer {token}'}

# 2. Get orders
req = urllib.request.Request(f'{BASE}/api/vendor/orders/', headers=headers)
with urllib.request.urlopen(req) as r:
    orders_resp = json.loads(r.read().decode('utf-8'))
    print("\nORDERS COUNT:", orders_resp.get('count'))
    for o in orders_resp.get('orders', []):
        print(f" -> {o['order_number']}: {o['customer_name']} | {o['status']} | Rs.{o['vendor_subtotal']} | Items: {o['item_count']}")

# 3. Sales overview
req = urllib.request.Request(f'{BASE}/api/vendor/sales/overview/', headers=headers)
with urllib.request.urlopen(req) as r:
    sales_resp = json.loads(r.read().decode('utf-8'))
    print("\nSALES OVERVIEW KPIS:", sales_resp.get('kpis'))

# 4. Earnings overview
req = urllib.request.Request(f'{BASE}/api/vendor/earnings/overview/', headers=headers)
with urllib.request.urlopen(req) as r:
    earn_resp = json.loads(r.read().decode('utf-8'))
    print("\nBALANCE SUMMARY:", earn_resp.get('balance_summary'))

# 5. Payouts
req = urllib.request.Request(f'{BASE}/api/vendor/payout/history/', headers=headers)
with urllib.request.urlopen(req) as r:
    pay_resp = json.loads(r.read().decode('utf-8'))
    print("\nPAYOUTS COUNT:", pay_resp.get('count'))
    for p in pay_resp.get('payouts', []):
        print(f" -> {p['payout_number']}: Rs.{p['amount']} | Status: {p['status']} | Bank: {p['bank_name']}")
