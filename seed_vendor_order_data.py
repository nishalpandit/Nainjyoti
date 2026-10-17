import os
import django
import random
from decimal import Decimal
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from nainjyoti.models import (
    VendorProfile, Category, Product, Order, OrderItem,
    OrderStatusHistory, VendorEarning, VendorPayout, StockLog
)

def seed_vendor_data():
    print("=" * 65)
    print(" SEEDING ALL DATA FOR VENDOR: merchant@crafts.in ")
    print("=" * 65)

    # 1. Setup User and Vendor Profile
    user, _ = User.objects.get_or_create(username='merchant@crafts.in', defaults={'email': 'merchant@crafts.in'})
    user.set_password('SellerSecure@2026')
    user.first_name = 'Tariq'
    user.last_name = 'Butt'
    user.email = 'merchant@crafts.in'
    user.save()
    print("[1] User 'merchant@crafts.in' password updated to 'SellerSecure@2026'.")

    vp, _ = VendorProfile.objects.get_or_create(user=user, defaults={
        'business_name': 'Kashmir Pashmina & Crafts',
        'owner_name': 'Tariq Butt',
        'phone': '9876543210',
        'status': 'APPROVED'
    })
    vp.business_name = 'Kashmir Pashmina & Crafts'
    vp.owner_name = 'Tariq Butt'
    vp.phone = '9876543210'
    vp.bank_name = 'HDFC Bank'
    vp.account_number = '50100492817291'
    vp.ifsc_code = 'HDFC0000123'
    vp.status = 'APPROVED'
    # Keep user's known token or set it
    if not vp.auth_token:
        vp.auth_token = '589031eb3c3b5a16bd354e88aa884e9611a827b9145f08c3d1beb090c8674584'
    vp.save()
    print(f"[2] VendorProfile #{vp.id} ('{vp.business_name}') is APPROVED with token: {vp.auth_token}")

    # 2. Reassign ALL existing products in the DB to this vendor
    assigned_count = Product.objects.exclude(vendor=vp).update(vendor=vp)
    print(f"[3] Reassigned {assigned_count} existing products to vendor #{vp.id}.")

    # Categories
    cat_crafts, _ = Category.objects.get_or_create(name='Handicrafts & Art', defaults={'status': 'ACTIVE'})
    cat_clothing, _ = Category.objects.get_or_create(name='Ethnic Wear & Shawls', defaults={'status': 'ACTIVE'})
    cat_gourmet, _ = Category.objects.get_or_create(name='Gourmet & Spices', defaults={'status': 'ACTIVE'})
    cat_home, _ = Category.objects.get_or_create(name='Home Decor & Pottery', defaults={'status': 'ACTIVE'})
    cat_elec, _ = Category.objects.get_or_create(name='Electronics & Gadgets', defaults={'status': 'ACTIVE'})

    # Catalog definition
    catalog = [
        {
            'sku': 'PASH-SOZNI-01',
            'name': 'Authentic Kashmiri Sozni Hand-Embroidered Pashmina Shawl',
            'category': cat_clothing,
            'price': Decimal('8999.00'),
            'stock': 35,
            'description': 'Pure 100% fine Cashmere wool handwoven in Srinagar with traditional Sozni needlework.'
        },
        {
            'sku': 'PASH-WOVEN-02',
            'name': 'Pure Pashmina Shawl Handwoven Classic',
            'category': cat_clothing,
            'price': Decimal('4999.00'),
            'stock': 40,
            'description': 'Classic ultra-soft handwoven Pashmina shawl with delicate fringed borders.'
        },
        {
            'sku': 'SAFFRON-5G-01',
            'name': 'Kashmir Valley Pure Saffron (Kesar) Grade A+ 5g',
            'category': cat_gourmet,
            'price': Decimal('1499.00'),
            'stock': 120,
            'description': 'Certified Pampore saffron threads known for rich deep aroma, natural color, and purity.'
        },
        {
            'sku': 'KAHWA-TEA-250G',
            'name': 'Kashmiri Kahwa Green Tea with Saffron & Almonds 250g',
            'category': cat_gourmet,
            'price': Decimal('649.00'),
            'stock': 85,
            'description': 'Traditional whole-leaf green tea blended with cinnamon, cardamom, pure saffron, and roasted almond slivers.'
        },
        {
            'sku': 'WOOD-BOX-01',
            'name': 'Carved Walnut Wood Jewellery Box Handcrafted',
            'category': cat_crafts,
            'price': Decimal('2499.00'),
            'stock': 25,
            'description': 'Handcrafted from seasoned Kashmiri walnut wood with intricate chinar leaf floral carvings.'
        },
        {
            'sku': 'MACHE-BOWL-01',
            'name': 'Handmade Kashmiri Paper Mache Decorative Bowl',
            'category': cat_crafts,
            'price': Decimal('1199.00'),
            'stock': 30,
            'description': 'Vibrant paper mache bowl painted with intricate Mughal motifs and gold leaf highlights.'
        },
        {
            'sku': 'POTTERY-BLUE-VASE',
            'name': 'Handmade Blue Ceramic Vase Traditional Floral',
            'category': cat_home,
            'price': Decimal('1299.00'),
            'stock': 50,
            'description': 'Glazed ceramic vase hand-painted in traditional cobalt blue artisan patterns.'
        },
        {
            'sku': 'POTTERY-PLATE-SET',
            'name': 'Jaipur Handcrafted Ceramic Dinner Plate Set of 2',
            'category': cat_home,
            'price': Decimal('899.00'),
            'stock': 60,
            'description': 'Stoneware handcrafted plates microwave and dishwasher safe with handcrafted brush strokes.'
        },
        {
            'sku': 'WATCH-PRO-001',
            'name': 'Wireless Noise Cancelling Smart Watch Pro',
            'category': cat_elec,
            'price': Decimal('3199.00'),
            'stock': 45,
            'description': 'Bluetooth calling smartwatch with AMOLED curved display and health sensor tracking.'
        },
        {
            'sku': 'KEY-MECH-002',
            'name': 'Ergonomic Wireless Mechanical Keyboard',
            'category': cat_elec,
            'price': Decimal('1599.00'),
            'stock': 30,
            'description': 'Dual-mode wireless mechanical keyboard with tactile blue switches and RGB backlight.'
        }
    ]

    products_map = {}
    for item in catalog:
        prod, _ = Product.objects.get_or_create(
            sku=item['sku'],
            defaults={
                'vendor': vp,
                'category': item['category'],
                'name': item['name'],
                'price': item['price'],
                'stock_quantity': item['stock'],
                'description': item['description'],
                'status': 'ACTIVE',
                'is_approved': True
            }
        )
        prod.vendor = vp
        prod.category = item['category']
        prod.name = item['name']
        prod.price = item['price']
        prod.stock_quantity = item['stock']
        prod.status = 'ACTIVE'
        prod.is_approved = True
        prod.save()
        products_map[item['sku']] = prod

    print(f"[4] Ensured 10 active catalog products for {vp.business_name}.")

    # 3. Clean up existing order items and orders to give clean, high quality state
    # Delete older earnings, payouts, history, items, and orders
    VendorEarning.objects.all().delete()
    VendorPayout.objects.all().delete()
    OrderStatusHistory.objects.all().delete()
    OrderItem.objects.all().delete()
    Order.objects.all().delete()
    print("[5] Reset order and financial tables for fresh, consistent data seeding.")

    # 4. Create comprehensive order dataset
    now = timezone.now()

    orders_to_create = [
        # 1. PENDING (Placed 25 minutes ago)
        {
            'order_number': 'ORD-20261017-101',
            'customer_name': 'Amit Singhania',
            'customer_phone': '9810123456',
            'customer_email': 'amit.singhania@gmail.com',
            'shipping_address': 'Flat 402, DLF Phase 5, Golf Course Road',
            'shipping_city': 'Gurgaon',
            'shipping_state': 'Haryana',
            'shipping_pincode': '122002',
            'payment_method': 'UPI',
            'payment_status': 'PAID',
            'status': 'PENDING',
            'created_delta': timedelta(minutes=25),
            'items': [
                {'sku': 'PASH-SOZNI-01', 'qty': 1}
            ],
            'history': [
                ('PENDING', 'Customer order placed successfully via UPI payment.')
            ]
        },
        # 2. CONFIRMED (Placed 2 hours ago, confirmed by vendor)
        {
            'order_number': 'ORD-20261017-102',
            'customer_name': 'Meera Nambiar',
            'customer_phone': '9845098765',
            'customer_email': 'meera.nambiar@yahoo.com',
            'shipping_address': 'Villa 14, Prestige Palms, Whitefield',
            'shipping_city': 'Bengaluru',
            'shipping_state': 'Karnataka',
            'shipping_pincode': '560066',
            'payment_method': 'CARD',
            'payment_status': 'PAID',
            'status': 'CONFIRMED',
            'created_delta': timedelta(hours=2),
            'items': [
                {'sku': 'SAFFRON-5G-01', 'qty': 2},
                {'sku': 'KAHWA-TEA-250G', 'qty': 1}
            ],
            'history': [
                ('PENDING', 'Order placed via Credit Card.'),
                ('CONFIRMED', 'Order verified and confirmed by vendor Tariq Butt.')
            ]
        },
        # 3. PROCESSING (Placed 4 hours ago, packaging)
        {
            'order_number': 'ORD-20261017-103',
            'customer_name': 'Rohit Sharma',
            'customer_phone': '9811223344',
            'customer_email': 'rohit.sharma@example.com',
            'shipping_address': 'Flat 502, Skyrise Heights, Bandra West',
            'shipping_city': 'Mumbai',
            'shipping_state': 'Maharashtra',
            'shipping_pincode': '400050',
            'payment_method': 'PREPAID',
            'payment_status': 'PAID',
            'status': 'PROCESSING',
            'created_delta': timedelta(hours=4),
            'items': [
                {'sku': 'WATCH-PRO-001', 'qty': 2}
            ],
            'history': [
                ('PENDING', 'Prepaid order placed.'),
                ('CONFIRMED', 'Stock allocated in warehouse.'),
                ('PROCESSING', 'Quality checked and packed in protective carton.')
            ]
        },
        # 4. PROCESSING (Placed 6 hours ago, COD)
        {
            'order_number': 'ORD-20261017-104',
            'customer_name': 'Tanya Kapoor',
            'customer_phone': '9814088776',
            'customer_email': 'tanya.kapoor@outlook.com',
            'shipping_address': 'House 112, Sector 8-C',
            'shipping_city': 'Chandigarh',
            'shipping_state': 'Punjab',
            'shipping_pincode': '160018',
            'payment_method': 'COD',
            'payment_status': 'PENDING',
            'status': 'PROCESSING',
            'created_delta': timedelta(hours=6),
            'items': [
                {'sku': 'WOOD-BOX-01', 'qty': 1},
                {'sku': 'KAHWA-TEA-250G', 'qty': 2}
            ],
            'history': [
                ('PENDING', 'Cash on Delivery order placed.'),
                ('CONFIRMED', 'Customer phone verification completed.'),
                ('PROCESSING', 'Order being boxed for courier pickup.')
            ]
        },
        # 5. SHIPPED (Dispatched yesterday via Delhivery)
        {
            'order_number': 'ORD-20261017-105',
            'customer_name': 'Priya Patel',
            'customer_phone': '9876501234',
            'customer_email': 'priya.p@example.com',
            'shipping_address': 'House No 12, Navrangpura',
            'shipping_city': 'Ahmedabad',
            'shipping_state': 'Gujarat',
            'shipping_pincode': '380009',
            'payment_method': 'COD',
            'payment_status': 'PENDING',
            'status': 'SHIPPED',
            'courier_name': 'Delhivery Express',
            'tracking_number': 'DEL-99281726',
            'created_delta': timedelta(days=1),
            'items': [
                {'sku': 'KEY-MECH-002', 'qty': 1}
            ],
            'history': [
                ('PENDING', 'Order placed.'),
                ('CONFIRMED', 'Order confirmed.'),
                ('PROCESSING', 'Packaging completed.'),
                ('SHIPPED', 'Dispatched via Delhivery Express tracking DEL-99281726.')
            ]
        },
        # 6. SHIPPED (Dispatched 1.5 days ago via BlueDart)
        {
            'order_number': 'ORD-20261017-106',
            'customer_name': 'Vikram Aditya Rao',
            'customer_phone': '9849011223',
            'customer_email': 'vikram.rao@gmail.com',
            'shipping_address': 'Plot 45, Jubilee Hills, Road No. 36',
            'shipping_city': 'Hyderabad',
            'shipping_state': 'Telangana',
            'shipping_pincode': '500033',
            'payment_method': 'PREPAID',
            'payment_status': 'PAID',
            'status': 'SHIPPED',
            'courier_name': 'BlueDart Express',
            'tracking_number': 'BD-7719280',
            'created_delta': timedelta(days=1, hours=12),
            'items': [
                {'sku': 'PASH-WOVEN-02', 'qty': 1},
                {'sku': 'POTTERY-BLUE-VASE', 'qty': 1}
            ],
            'history': [
                ('PENDING', 'Order placed via Net Banking.'),
                ('PROCESSING', 'Handcrafted packing done.'),
                ('SHIPPED', 'Handed over to BlueDart Air Express Hub.')
            ]
        },
        # 7. DELIVERED (Delivered 2 days ago, earnings AVAILABLE)
        {
            'order_number': 'ORD-20261017-107',
            'customer_name': 'Ananya Verma',
            'customer_phone': '9876543210',
            'customer_email': 'ananya@example.com',
            'shipping_address': 'Flat 402, Lotus Greens, Sector 78',
            'shipping_city': 'Noida',
            'shipping_state': 'Uttar Pradesh',
            'shipping_pincode': '201301',
            'payment_method': 'PREPAID',
            'payment_status': 'PAID',
            'status': 'DELIVERED',
            'courier_name': 'BlueDart Express',
            'tracking_number': 'BD-8849102',
            'created_delta': timedelta(days=3),
            'delivered_delta': timedelta(days=2),
            'items': [
                {'sku': 'PASH-SOZNI-01', 'qty': 1}
            ],
            'history': [
                ('PENDING', 'Prepaid order placed.'),
                ('PROCESSING', 'Handled with care.'),
                ('SHIPPED', 'In transit via BlueDart.'),
                ('DELIVERED', 'Delivered to customer doorstep and verified.')
            ]
        },
        # 8. DELIVERED (Delivered 4 days ago via DTDC, earnings AVAILABLE)
        {
            'order_number': 'ORD-20261017-108',
            'customer_name': 'Deepak Sengupta',
            'customer_phone': '9830022334',
            'customer_email': 'deepak.sengupta@kolkata.in',
            'shipping_address': 'Apt 3B, Ballygunge Circular Road',
            'shipping_city': 'Kolkata',
            'shipping_state': 'West Bengal',
            'shipping_pincode': '700019',
            'payment_method': 'UPI',
            'payment_status': 'PAID',
            'status': 'DELIVERED',
            'courier_name': 'DTDC Express',
            'tracking_number': 'DTDC-4401928',
            'created_delta': timedelta(days=5),
            'delivered_delta': timedelta(days=4),
            'items': [
                {'sku': 'SAFFRON-5G-01', 'qty': 3},
                {'sku': 'KAHWA-TEA-250G', 'qty': 2}
            ],
            'history': [
                ('PENDING', 'UPI payment received.'),
                ('PROCESSING', 'Order packed.'),
                ('SHIPPED', 'Handed over to DTDC.'),
                ('DELIVERED', 'Delivered and signed by recipient.')
            ]
        },
        # 9. DELIVERED (Delivered 6 days ago via Shadowfax, earnings AVAILABLE)
        {
            'order_number': 'ORD-20261017-109',
            'customer_name': 'Sunita Reddy',
            'customer_phone': '9840019283',
            'customer_email': 'sunita.reddy@gmail.com',
            'shipping_address': 'No. 8, Boat Club Road, R.A. Puram',
            'shipping_city': 'Chennai',
            'shipping_state': 'Tamil Nadu',
            'shipping_pincode': '600028',
            'payment_method': 'CARD',
            'payment_status': 'PAID',
            'status': 'DELIVERED',
            'courier_name': 'Shadowfax Logistics',
            'tracking_number': 'SFX-9182740',
            'created_delta': timedelta(days=7),
            'delivered_delta': timedelta(days=6),
            'items': [
                {'sku': 'POTTERY-PLATE-SET', 'qty': 2},
                {'sku': 'WOOD-BOX-01', 'qty': 1}
            ],
            'history': [
                ('PENDING', 'Card payment approved.'),
                ('PROCESSING', 'Bubble-wrapped and boxed.'),
                ('SHIPPED', 'Dispatched with Shadowfax.'),
                ('DELIVERED', 'Delivered safely at security desk.')
            ]
        },
        # 10. CANCELLED (Customer cancelled before dispatch)
        {
            'order_number': 'ORD-20261017-110',
            'customer_name': 'Nikhil Joshi',
            'customer_phone': '9822014567',
            'customer_email': 'nikhil.joshi@pune.ac.in',
            'shipping_address': 'B-10, Koregaon Park Annexe',
            'shipping_city': 'Pune',
            'shipping_state': 'Maharashtra',
            'shipping_pincode': '411001',
            'payment_method': 'COD',
            'payment_status': 'FAILED',
            'status': 'CANCELLED',
            'created_delta': timedelta(days=2),
            'items': [
                {'sku': 'WATCH-PRO-001', 'qty': 1}
            ],
            'history': [
                ('PENDING', 'COD order created.'),
                ('CANCELLED', 'Customer requested cancellation due to wrong delivery address.')
            ]
        },
        # 11. RETURNED (Customer returned item after delivery)
        {
            'order_number': 'ORD-20261017-111',
            'customer_name': 'Kavita Nair',
            'customer_phone': '9847055443',
            'customer_email': 'kavita.nair@cochin.org',
            'shipping_address': 'Hill View Villa, Marine Drive',
            'shipping_city': 'Kochi',
            'shipping_state': 'Kerala',
            'shipping_pincode': '682011',
            'payment_method': 'PREPAID',
            'payment_status': 'REFUNDED',
            'status': 'RETURNED',
            'courier_name': 'Delhivery Return Pickup',
            'tracking_number': 'RET-DLV-381920',
            'created_delta': timedelta(days=9),
            'delivered_delta': timedelta(days=7),
            'items': [
                {'sku': 'MACHE-BOWL-01', 'qty': 2}
            ],
            'history': [
                ('PENDING', 'Prepaid order placed.'),
                ('SHIPPED', 'Dispatched to customer.'),
                ('DELIVERED', 'Delivered to customer.'),
                ('RETURNED', 'Customer returned package; received at vendor return facility.')
            ]
        }
    ]

    for ord_spec in orders_to_create:
        created_time = now - ord_spec['created_delta']

        # Calculate total
        total_amt = Decimal('0.00')
        item_rows = []
        for it in ord_spec['items']:
            p = products_map[it['sku']]
            subtotal = p.price * it['qty']
            total_amt += subtotal
            item_rows.append((p, it['qty'], subtotal))

        order = Order.objects.create(
            order_number=ord_spec['order_number'],
            customer_name=ord_spec['customer_name'],
            customer_phone=ord_spec['customer_phone'],
            customer_email=ord_spec['customer_email'],
            shipping_address=ord_spec['shipping_address'],
            shipping_city=ord_spec['shipping_city'],
            shipping_state=ord_spec['shipping_state'],
            shipping_pincode=ord_spec['shipping_pincode'],
            total_amount=total_amt,
            payment_method=ord_spec['payment_method'],
            payment_status=ord_spec['payment_status'],
            status=ord_spec['status']
        )
        Order.objects.filter(id=order.id).update(created_at=created_time)

        for prod, qty, subtotal in item_rows:
            item = OrderItem.objects.create(
                order=order,
                vendor=vp,
                product=prod,
                product_name=prod.name,
                product_sku=prod.sku,
                price=prod.price,
                quantity=qty,
                total_price=subtotal,
                status=ord_spec['status'],
                courier_name=ord_spec.get('courier_name', ''),
                tracking_number=ord_spec.get('tracking_number', '')
            )
            OrderItem.objects.filter(id=item.id).update(created_at=created_time)

            # Record StockLog
            StockLog.objects.create(
                product=prod,
                vendor=vp,
                movement_type='SALE',
                quantity_changed=-qty,
                previous_stock=prod.stock_quantity + qty,
                new_stock=prod.stock_quantity,
                reason=f"Sold via Order {order.order_number}",
                reference_id=order.order_number
            )

        # Status History
        prev_st = 'PENDING'
        for step_st, notes in ord_spec['history']:
            OrderStatusHistory.objects.create(
                order=order,
                order_item=None,
                vendor=vp,
                old_status=prev_st,
                new_status=step_st,
                notes=notes
            )
            prev_st = step_st

        # Create VendorEarning for DELIVERED and PROCESSING/SHIPPED orders
        if ord_spec['status'] == 'DELIVERED':
            comm_rate = Decimal('5.00')
            comm_amt = round(total_amt * (comm_rate / Decimal('100.00')), 2)
            net_amt = total_amt - comm_amt
            VendorEarning.objects.create(
                vendor=vp,
                order=order,
                gross_amount=total_amt,
                commission_rate=comm_rate,
                commission_amount=comm_amt,
                net_amount=net_amt,
                status='AVAILABLE',
                cleared_at=now - ord_spec.get('delivered_delta', timedelta(days=1))
            )
        elif ord_spec['status'] in ['PROCESSING', 'SHIPPED']:
            comm_rate = Decimal('5.00')
            comm_amt = round(total_amt * (comm_rate / Decimal('100.00')), 2)
            net_amt = total_amt - comm_amt
            VendorEarning.objects.create(
                vendor=vp,
                order=order,
                gross_amount=total_amt,
                commission_rate=comm_rate,
                commission_amount=comm_amt,
                net_amount=net_amt,
                status='PENDING',
                cleared_at=None
            )

    print(f"[6] Created {len(orders_to_create)} orders with history & earnings for {vp.business_name}.")

    # 5. Create realistic Payouts / Settlements for Vendor
    payout1 = VendorPayout.objects.create(
        payout_number='PAY-20261010-1011',
        vendor=vp,
        amount=Decimal('8000.00'),
        bank_name='HDFC Bank',
        account_number='50100492817291',
        ifsc_code='HDFC0000123',
        status='COMPLETED',
        utr_number='NEFT-HDFC-9918273645',
        admin_notes='Settled via bi-weekly vendor bank disbursement cycle.',
        processed_at=now - timedelta(days=7)
    )

    payout2 = VendorPayout.objects.create(
        payout_number='PAY-20261016-5520',
        vendor=vp,
        amount=Decimal('3500.00'),
        bank_name='HDFC Bank',
        account_number='50100492817291',
        ifsc_code='HDFC0000123',
        status='PENDING',
        admin_notes='Requested by vendor Tariq Butt; queued for batch clearance.'
    )
    print(f"[7] Created 2 vendor payouts (1 COMPLETED Rs. 8000, 1 PENDING Rs. 3500).")

    print("\n" + "=" * 65)
    print(" VENDOR DATA SEEDING COMPLETED SUCCESSFULLY! ")
    print("=" * 65)

if __name__ == '__main__':
    seed_vendor_data()
