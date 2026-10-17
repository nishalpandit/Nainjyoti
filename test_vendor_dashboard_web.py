import urllib.request
import urllib.parse
import json
import re

BASE_URL = "http://127.0.0.1:8000"

def test_pages():
    pages = [
        ('/vendor-dashboard/', 'Dashboard Overview', ['Tariq Butt', 'Kashmir Pashmina &amp; Crafts', 'Gross Sales', '7-Day Store Performance']),
        ('/vendor-dashboard/products/', 'Products Catalog', ['Product Catalog', 'Total Listings', 'Add product']),
        ('/vendor-dashboard/products/add/', 'Add Product', ['Add a Product', 'Selling Price (₹)']),
        ('/vendor-dashboard/orders/', 'Orders Management', ['Customer Orders', 'ORD-20261017-101', 'Amit Singhania']),
        ('/vendor-dashboard/inventory/', 'Inventory Ledger', ['Inventory &amp; Stock Ledger', 'Current Stock Levels', 'Audit Trail']),
        ('/vendor-dashboard/earnings/', 'Earnings & Financials', ['Earnings &amp; Financial Analytics', 'Platform Fee (5%)', 'Order-by-Order Earnings Ledger']),
        ('/vendor-dashboard/withdrawals/', 'Withdrawals & Settlements', ['Withdrawals &amp; Settlements', 'Available for Payout', 'Disbursement &amp; Settlement History']),
        ('/vendor-dashboard/settings/', 'Store Settings', ['Store &amp; Banking Settings', '589031eb3c3b5a16bd354e88aa884e9611a827b9145f08c3d1beb090c8674584', 'HDFC Bank']),
    ]

    print("=" * 65)
    print(" TESTING DYNAMIC VENDOR WEB DASHBOARD PAGES ")
    print("=" * 65)

    all_passed = True
    for path, name, expected_strings in pages:
        url = f"{BASE_URL}{path}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                html = resp.read().decode('utf-8')
                
                missing = [s for s in expected_strings if s not in html]
                if status == 200 and not missing:
                    print(f" [PASS] {status} - {name} ({path})")
                else:
                    print(f" [FAIL] {status} - {name} ({path}) - Missing: {missing}")
                    all_passed = False
        except Exception as e:
            print(f" [ERROR] {name} ({path}): {e}")
            all_passed = False

    # Also test Order Detail page for the first order
    try:
        import os, django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
        django.setup()
        from nainjyoti.models import Order
        first_ord = Order.objects.first()
        if first_ord:
            detail_path = f"/vendor-dashboard/orders/{first_ord.id}/"
            req = urllib.request.Request(f"{BASE_URL}{detail_path}")
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                html = resp.read().decode('utf-8')
                if status == 200 and first_ord.order_number in html:
                    print(f" [PASS] {status} - Order Detail ({detail_path}) - Verified #{first_ord.order_number}")
                else:
                    print(f" [FAIL] {status} - Order Detail ({detail_path})")
                    all_passed = False
    except Exception as e:
        print(f" [ERROR] Order Detail: {e}")
        all_passed = False

    print("=" * 65)
    if all_passed:
        print(" ALL DYNAMIC VENDOR DASHBOARD PAGES VERIFIED 100%! ")
    else:
        print(" SOME PAGES FAILED VERIFICATION ")
    print("=" * 65)

if __name__ == '__main__':
    test_pages()
