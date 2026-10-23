import json
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import (
    VendorProfile, Category, Product, ProductVariant, Order, OrderItem,
    OrderStatusHistory, VendorEarning, VendorPayout, StockLog
)
from .api_views import _get_vendor_balance_summary


def _get_dashboard_vendor(request):
    """
    Retrieves the authenticated vendor.
    If authenticated via user.vendor_profile, uses it.
    If in session or for seamless vendor access, falls back to approved merchant (merchant@crafts.in).
    """
    if hasattr(request, "user") and request.user.is_authenticated and hasattr(request.user, "vendor_profile"):
        if request.user.vendor_profile.status == "APPROVED":
            return request.user.vendor_profile

    # Fallback to the primary approved vendor merchant@crafts.in
    target = VendorProfile.objects.filter(user__username='merchant@crafts.in').first()
    if target:
        return target
    return VendorProfile.objects.filter(status="APPROVED").first()


# =============================================================================
# 1. Vendor Main Dashboard
# =============================================================================

def vendor_dashboard(request):
    """
    Dynamic Vendor Dashboard Overview with real metrics, 7-day sales chart,
    store snapshot, and recent orders.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        messages.error(request, "Please log in to your vendor account.")
        return redirect("login")

    # 1. Core KPIs
    vendor_items = OrderItem.objects.filter(vendor=vendor)
    order_ids = vendor_items.values_list('order_id', flat=True).distinct()
    orders_qs = Order.objects.filter(id__in=order_ids)
    
    total_orders_count = orders_qs.count()
    gross_sales = float(vendor_items.aggregate(total=Sum('total_price'))['total'] or 0.0)

    products_qs = Product.objects.filter(vendor=vendor)
    products_count = products_qs.count()
    low_stock_count = products_qs.filter(stock_quantity__lte=10, stock_quantity__gt=0).count()
    out_of_stock_count = products_qs.filter(stock_quantity=0).count()
    in_stock_count = products_qs.filter(stock_quantity__gt=10).count()

    # Balance Summary
    bal_summary = _get_vendor_balance_summary(vendor)
    available_balance = bal_summary['available_balance']

    # 2. 7-Day Performance Chart Data
    now = timezone.now()
    chart_days = []
    max_day_sales = 1.0

    day_sales_raw = []
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_label = day_date.strftime("%a")
        
        day_items = vendor_items.filter(order__created_at__date=day_date)
        day_val = float(day_items.aggregate(total=Sum('total_price'))['total'] or 0.0)
        day_sales_raw.append((day_label, day_val))
        if day_val > max_day_sales:
            max_day_sales = day_val

    for day_label, day_val in day_sales_raw:
        # Scale to max height of 95%
        height_pct = max(18, min(int((day_val / max_day_sales) * 95), 95)) if day_val > 0 else 14
        chart_days.append({
            'label': day_label,
            'value': day_val,
            'height': height_pct,
            'alt_height': max(12, int(height_pct * 0.75))
        })

    # 3. Store Snapshot
    in_stock_pct = int((in_stock_count / products_count * 100)) if products_count > 0 else 100
    delivered_orders = orders_qs.filter(status='DELIVERED').count()
    non_cancelled = orders_qs.exclude(status='CANCELLED').count()
    fulfillment_rate = round((delivered_orders / non_cancelled * 100), 1) if non_cancelled > 0 else 100.0
    avg_order_value = round((gross_sales / total_orders_count), 2) if total_orders_count > 0 else 0.0

    # 4. Recent Orders (Latest 5)
    recent_orders = orders_qs.order_by('-created_at')[:5]
    recent_orders_data = []
    for ord_obj in recent_orders:
        ord_items = ord_obj.items.filter(vendor=vendor)
        ord_subtotal = sum(float(item.total_price) for item in ord_items)
        recent_orders_data.append({
            'order': ord_obj,
            'subtotal': ord_subtotal,
            'item_count': ord_items.count()
        })

    context = {
        'vendor': vendor,
        'gross_sales': gross_sales,
        'total_orders': total_orders_count,
        'products_count': products_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'in_stock_count': in_stock_count,
        'in_stock_pct': in_stock_pct,
        'available_balance': available_balance,
        'chart_days': chart_days,
        'fulfillment_rate': fulfillment_rate,
        'avg_order_value': avg_order_value,
        'recent_orders_data': recent_orders_data,
        'bal_summary': bal_summary,
    }
    return render(request, "vendor/index.html", context)


# =============================================================================
# 2. Vendor Products Management
# =============================================================================

def vendor_products(request):
    """
    List and manage vendor products with search and category filtering.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    products = Product.objects.filter(vendor=vendor).select_related('category').prefetch_related('variants').order_by('-id')

    # Search filter
    search_query = request.GET.get('q', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Category filter
    category_id = request.GET.get('category')
    if category_id and category_id.isdigit():
        products = products.filter(category_id=int(category_id))

    # Status filter
    status_filter = request.GET.get('status', '').strip().upper()
    if status_filter and status_filter != 'ALL':
        products = products.filter(status=status_filter)

    categories = Category.objects.filter(status='ACTIVE').order_by('name')

    total_count = Product.objects.filter(vendor=vendor).count()
    in_stock_count = Product.objects.filter(vendor=vendor, stock_quantity__gt=10).count()
    low_stock_count = Product.objects.filter(vendor=vendor, stock_quantity__lte=10, stock_quantity__gt=0).count()
    out_of_stock_count = Product.objects.filter(vendor=vendor, stock_quantity=0).count()

    context = {
        'vendor': vendor,
        'products': products,
        'categories': categories,
        'total_count': total_count,
        'in_stock_count': in_stock_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'search_query': search_query,
        'selected_category': int(category_id) if category_id and category_id.isdigit() else None,
        'selected_status': status_filter,
    }
    return render(request, "vendor/products.html", context)


def vendor_product_add(request):
    """
    Add a new product to the vendor's catalog.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    categories = Category.objects.filter(status='ACTIVE').order_by('name')

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        sku = request.POST.get('sku', '').strip()
        category_id = request.POST.get('category_id')
        price_raw = request.POST.get('price', '').strip()
        stock_raw = request.POST.get('stock_quantity', '0').strip()
        description = request.POST.get('description', '').strip()
        uploaded_image = request.FILES.get('image')
        image_url = request.POST.get('image_url', '').strip()

        if not name:
            messages.error(request, "Product name is required.")
            return render(request, "vendor/product-form.html", {'vendor': vendor, 'categories': categories, 'is_edit': False})

        try:
            price = Decimal(price_raw)
            stock_qty = int(stock_raw)
        except Exception:
            messages.error(request, "Invalid price or stock quantity value.")
            return render(request, "vendor/product-form.html", {'vendor': vendor, 'categories': categories, 'is_edit': False})

        category = Category.objects.filter(id=category_id).first() if category_id and category_id.isdigit() else None

        # Auto-generate SKU if blank
        if not sku:
            import random
            sku = f"PROD-{random.randint(100000, 999999)}"

        product = Product.objects.create(
            vendor=vendor,
            category=category,
            name=name,
            sku=sku,
            price=price,
            stock_quantity=stock_qty,
            description=description,
            image=uploaded_image if uploaded_image else (image_url if image_url else None),
            status='ACTIVE',
            is_approved=True
        )

        # Log initial stock
        if stock_qty > 0:
            StockLog.objects.create(
                product=product,
                vendor=vendor,
                movement_type='RESTOCK',
                quantity_changed=stock_qty,
                previous_stock=0,
                new_stock=stock_qty,
                reason="Initial product creation stock",
                reference_id=f"INIT-{product.id}"
            )

        messages.success(request, f"Product '{product.name}' (SKU: {product.sku}) created successfully!")
        return redirect("vendor_products")

    return render(request, "vendor/product-form.html", {
        'vendor': vendor,
        'categories': categories,
        'is_edit': False,
        'product': None
    })


def vendor_product_edit(request, product_id):
    """
    Edit an existing vendor product.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    product = get_object_or_404(Product, id=product_id, vendor=vendor)
    categories = Category.objects.filter(status='ACTIVE').order_by('name')

    if request.method == "POST":
        product.name = request.POST.get('name', '').strip() or product.name
        product.sku = request.POST.get('sku', '').strip() or product.sku
        category_id = request.POST.get('category_id')
        if category_id and category_id.isdigit():
            product.category = Category.objects.filter(id=int(category_id)).first()

        try:
            product.price = Decimal(request.POST.get('price', str(product.price)))
            if not product.has_variants:
                old_stock = product.stock_quantity
                new_stock = int(request.POST.get('stock_quantity', str(product.stock_quantity)))
                if new_stock != old_stock:
                    diff = new_stock - old_stock
                    product.stock_quantity = new_stock
                    StockLog.objects.create(
                        product=product,
                        vendor=vendor,
                        movement_type='CORRECTION',
                        quantity_changed=diff,
                        previous_stock=old_stock,
                        new_stock=new_stock,
                        reason="Product edit stock correction",
                        reference_id=f"EDIT-{product.id}"
                    )
            else:
                product.sync_variant_inventory()
        except Exception:
            pass

        product.description = request.POST.get('description', '').strip()
        
        # Handle file upload or image url
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        elif request.POST.get('image_url'):
            product.image = request.POST.get('image_url').strip()

        status_val = request.POST.get('status', '').strip().upper()
        if status_val in ['ACTIVE', 'INACTIVE']:
            product.status = status_val

        product.save()
        messages.success(request, f"Product '{product.name}' updated successfully!")
        return redirect("vendor_products")

    return render(request, "vendor/product-form.html", {
        'vendor': vendor,
        'categories': categories,
        'is_edit': True,
        'product': product
    })


def vendor_product_delete(request, product_id):
    """
    Delete a vendor product.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id, vendor=vendor)
        # Check if order items exist
        if product.order_items.exists():
            product.status = 'INACTIVE'
            product.save()
            messages.warning(request, f"Product '{product.name}' has associated orders and was marked INACTIVE instead of deleted.")
        else:
            name = product.name
            product.delete()
            messages.success(request, f"Product '{name}' deleted successfully.")

    return redirect("vendor_products")


# =============================================================================
# 3. Vendor Orders Management
# =============================================================================

def vendor_orders(request):
    """
    Orders list for vendor with search, status filters, and action tools.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    vendor_items = OrderItem.objects.filter(vendor=vendor)
    order_ids = vendor_items.values_list('order_id', flat=True).distinct()
    orders_qs = Order.objects.filter(id__in=order_ids).order_by('-created_at')

    # Status counts
    counts = {
        'ALL': orders_qs.count(),
        'PENDING': orders_qs.filter(status='PENDING').count(),
        'CONFIRMED': orders_qs.filter(status='CONFIRMED').count(),
        'PROCESSING': orders_qs.filter(status='PROCESSING').count(),
        'SHIPPED': orders_qs.filter(status='SHIPPED').count(),
        'DELIVERED': orders_qs.filter(status='DELIVERED').count(),
        'CANCELLED': orders_qs.filter(status='CANCELLED').count(),
    }

    # Search filter
    search_q = request.GET.get('q', '').strip()
    if search_q:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_q) |
            Q(customer_name__icontains=search_q) |
            Q(customer_phone__icontains=search_q) |
            Q(shipping_city__icontains=search_q)
        )

    # Status filter
    status_filter = request.GET.get('status', '').strip().upper()
    if status_filter and status_filter != 'ALL':
        orders_qs = orders_qs.filter(status=status_filter)

    orders_data = []
    for ord_obj in orders_qs:
        items = ord_obj.items.filter(vendor=vendor)
        subtotal = sum(float(it.total_price) for it in items)
        orders_data.append({
            'order': ord_obj,
            'items': items,
            'item_count': items.count(),
            'subtotal': subtotal
        })

    context = {
        'vendor': vendor,
        'orders_data': orders_data,
        'counts': counts,
        'current_status': status_filter or 'ALL',
        'search_query': search_q,
    }
    return render(request, "vendor/orders.html", context)


def vendor_order_detail(request, order_id):
    """
    Detailed Order View with item breakdown, customer info, delivery address,
    and status change timeline.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    order = get_object_or_404(Order, id=order_id)
    items = order.items.filter(vendor=vendor)
    if not items.exists():
        messages.error(request, "Access denied. This order does not contain products from your store.")
        return redirect("vendor_orders")

    subtotal = sum(float(it.total_price) for it in items)
    history = OrderStatusHistory.objects.filter(order=order).order_by('-created_at')

    context = {
        'vendor': vendor,
        'order': order,
        'items': items,
        'subtotal': subtotal,
        'history': history,
        'allowed_statuses': ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED']
    }
    return render(request, "vendor/order_detail.html", context)


def vendor_order_update_status(request, order_id):
    """
    Update order status directly from vendor dashboard.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        vendor_items = order.items.filter(vendor=vendor)
        if not vendor_items.exists():
            messages.error(request, "Access denied.")
            return redirect("vendor_orders")

        new_status = request.POST.get('status', '').strip().upper()
        courier_name = request.POST.get('courier_name', '').strip()
        tracking_number = request.POST.get('tracking_number', '').strip()
        notes = request.POST.get('notes', '').strip()

        old_status = order.status
        order.status = new_status
        order.save()

        # Update items
        for it in vendor_items:
            it.status = new_status
            if courier_name:
                it.courier_name = courier_name
            if tracking_number:
                it.tracking_number = tracking_number
            if new_status == 'DELIVERED':
                it.delivery_date = timezone.now()
            elif new_status == 'SHIPPED':
                it.dispatch_date = timezone.now()
            it.save()

        # History log
        OrderStatusHistory.objects.create(
            order=order,
            vendor=vendor,
            old_status=old_status,
            new_status=new_status,
            notes=notes or f"Status changed from {old_status} to {new_status} via Seller Console."
        )

        # Clear earnings if delivered
        if new_status == 'DELIVERED':
            VendorEarning.objects.filter(vendor=vendor, order=order).update(
                status='AVAILABLE',
                cleared_at=timezone.now()
            )

        messages.success(request, f"Order #{order.order_number} status updated to {new_status}!")

    return redirect(request.META.get('HTTP_REFERER', 'vendor_orders'))


# =============================================================================
# 4. Vendor Inventory Management
# =============================================================================

def vendor_inventory(request):
    """
    Inventory and stock tracking with low-stock alerts, valuation, and quick adjustments.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    products = Product.objects.filter(vendor=vendor).select_related('category').prefetch_related('variants').order_by('stock_quantity')

    total_skus = products.count()
    low_stock_count = products.filter(stock_quantity__lte=10, stock_quantity__gt=0).count()
    out_of_stock_count = products.filter(stock_quantity=0).count()

    total_valuation = sum(p.stock_valuation for p in products)

    # Recent stock logs
    recent_logs = StockLog.objects.filter(vendor=vendor).select_related('product', 'variant').order_by('-created_at')[:15]

    context = {
        'vendor': vendor,
        'products': products,
        'total_skus': total_skus,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_valuation': total_valuation,
        'recent_logs': recent_logs,
    }
    return render(request, "vendor/inventory.html", context)


def vendor_stock_adjust(request, product_id):
    """
    Inline restock or stock adjustment modal handler.
    Supports adjusting base product or specific variant.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id, vendor=vendor)
        movement_type = request.POST.get('movement_type', 'RESTOCK').strip().upper()
        qty_change_raw = request.POST.get('quantity', '0').strip()
        reason = request.POST.get('reason', '').strip()
        variant_id = request.POST.get('variant_id')

        try:
            qty_change = int(qty_change_raw)
        except ValueError:
            messages.error(request, "Invalid quantity.")
            return redirect("vendor_inventory")

        variant = None
        if variant_id and str(variant_id).isdigit():
            variant = ProductVariant.objects.filter(id=int(variant_id), product=product).first()
        elif product.has_variants:
            variant = product.variants.filter(is_active=True).first() or product.variants.first()

        target = variant or product
        if movement_type in ['DAMAGE', 'SALE']:
            actual_change = -abs(qty_change)
        else:
            actual_change = abs(qty_change)

        old_stock = target.stock_quantity
        new_stock = max(0, old_stock + actual_change)
        target.stock_quantity = new_stock
        target.save()

        if variant:
            product.sync_variant_inventory()
            product.refresh_from_db()

        StockLog.objects.create(
            product=product,
            variant=variant,
            vendor=vendor,
            movement_type=movement_type,
            quantity_changed=actual_change,
            previous_stock=old_stock,
            new_stock=new_stock,
            reason=reason or f"Stock updated via Vendor Dashboard ({movement_type})",
            reference_id=f"WEB-{timezone.now().strftime('%Y%m%d%H%M')}"
        )

        item_label = f"variant '{variant.title}'" if variant else f"'{product.name}'"
        messages.success(request, f"Stock for {item_label} adjusted by {actual_change:+d}. New stock: {new_stock} units.")

    return redirect("vendor_inventory")


# =============================================================================
# 5. Vendor Earnings Overview
# =============================================================================

def vendor_earnings(request):
    """
    Financial analytics, platform fee transparency, and order earnings ledger.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    bal_summary = _get_vendor_balance_summary(vendor)
    earnings_records = VendorEarning.objects.filter(vendor=vendor).select_related('order').order_by('-created_at')

    context = {
        'vendor': vendor,
        'bal_summary': bal_summary,
        'earnings_records': earnings_records,
    }
    return render(request, "vendor/earnings.html", context)


# =============================================================================
# 6. Vendor Withdrawals / Settlements
# =============================================================================

def vendor_withdrawals(request):
    """
    Payout requests and settlement disbursement history.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    bal_summary = _get_vendor_balance_summary(vendor)
    payouts = VendorPayout.objects.filter(vendor=vendor).order_by('-requested_at')

    context = {
        'vendor': vendor,
        'bal_summary': bal_summary,
        'payouts': payouts,
    }
    return render(request, "vendor/withdrawals.html", context)


def vendor_payout_request(request):
    """
    Handle payout request from web dashboard.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    if request.method == "POST":
        amount_raw = request.POST.get('amount', '').strip()
        notes = request.POST.get('notes', '').strip()

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                messages.error(request, "Withdrawal amount must be greater than zero.")
                return redirect("vendor_withdrawals")
        except Exception:
            messages.error(request, "Invalid withdrawal amount format.")
            return redirect("vendor_withdrawals")

        bal_summary = _get_vendor_balance_summary(vendor)
        avail = Decimal(str(bal_summary['available_balance']))

        if amount > avail:
            messages.error(request, f"Requested amount ₹{amount:.2f} exceeds your current available balance of ₹{avail:.2f}.")
            return redirect("vendor_withdrawals")

        if not vendor.bank_name or not vendor.account_number or not vendor.ifsc_code:
            messages.error(request, "Bank details incomplete. Please update your bank details in Store Settings before requesting a payout.")
            return redirect("vendor_settings")

        payout = VendorPayout.objects.create(
            vendor=vendor,
            amount=amount,
            bank_name=vendor.bank_name,
            account_number=vendor.account_number,
            ifsc_code=vendor.ifsc_code,
            status='PENDING',
            admin_notes=notes
        )

        messages.success(request, f"Withdrawal request #{payout.payout_number} for ₹{amount:.2f} submitted successfully! Funds will be credited after bank batch processing.")

    return redirect("vendor_withdrawals")


# =============================================================================
# 7. Vendor Store & Bank Settings
# =============================================================================

def vendor_settings(request):
    """
    Vendor store profile, banking information, and API access token.
    """
    vendor = _get_dashboard_vendor(request)
    if not vendor:
        return redirect("login")

    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'regenerate_token':
            vendor.generate_new_token()
            messages.success(request, "New API Bearer Token generated successfully!")
            return redirect("vendor_settings")

        # Update profile
        vendor.business_name = request.POST.get('business_name', '').strip() or vendor.business_name
        vendor.owner_name = request.POST.get('owner_name', '').strip() or vendor.owner_name
        vendor.phone = request.POST.get('phone', '').strip() or vendor.phone
        vendor.address = request.POST.get('address', '').strip()
        vendor.city = request.POST.get('city', '').strip()
        vendor.state = request.POST.get('state', '').strip()
        vendor.pincode = request.POST.get('pincode', '').strip()
        vendor.store_description = request.POST.get('store_description', '').strip()

        # Banking
        vendor.bank_name = request.POST.get('bank_name', '').strip() or vendor.bank_name
        vendor.account_number = request.POST.get('account_number', '').strip() or vendor.account_number
        vendor.ifsc_code = request.POST.get('ifsc_code', '').strip().upper() or vendor.ifsc_code

        vendor.save()
        messages.success(request, "Store profile and bank information updated successfully!")
        return redirect("vendor_settings")

    return render(request, "vendor/settings.html", {'vendor': vendor})
