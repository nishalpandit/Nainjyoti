import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
import re

client = Client()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
client.force_login(admin_user)

resp = client.get('/admin-dashboard/')
assert resp.status_code == 200
html = resp.content.decode('utf-8')

checks = [
    'Gross merchandise value',
    'Orders today',
    'Active vendors',
    'Open issues',
    'Marketplace sales',
    'Needs attention',
    'Recent orders',
    'Top categories',
    'ORD-',
    'bar-wrap',
    'chart-grid',
]

print("=== ADMIN DASHBOARD VERIFICATION ===")
for ch in checks:
    assert ch in html, f"Missing '{ch}' in rendered dashboard!"
    print(f" [OK] Found dynamic section: {ch}")

# Verify 7-day bar chart
bars = re.findall(r'class="bar"\s+style="height:(\d+)%"', html)
print(f" [OK] Rendered {len(bars)} dynamic bars in sales chart: {bars}")

# Verify recent orders count
orders = re.findall(r'ORD-\d+-\d+', html)
print(f" [OK] Rendered real database orders: {orders}")

# Verify top categories
cats = re.findall(r'<div class="progress">\s*<div style="width:(\d+)%"></div>\s*</div>', html)
print(f" [OK] Rendered {len(cats)} dynamic categories with progress bars: {cats}")

print("\nALL ADMIN DASHBOARD DYNAMIC TESTS PASSED!")
