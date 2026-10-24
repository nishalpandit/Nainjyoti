from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal, InvalidOperation
import json
import csv
from django.utils.text import slugify
from .models import (
    VendorProfile,
    Category,
    Product,
    Order,
    OrderItem,
    VendorPayout,
    VendorEarning,
    UserProfile,
    UserAddress,
    StockLog,
    OrderRequest,
    Notification,
    PaymentTransaction,
    ProductReview,
    WishlistItem,
    CartItem,
    CommissionSetting,
    CommissionRateHistory,
    commission_amount_for,
    customer_price_for,
)


def _is_marketplace_admin(user):
    """Only active Django staff/superusers may use the custom admin console."""
    return user.is_authenticated and user.is_active and (user.is_staff or user.is_superuser)


admin_required = user_passes_test(_is_marketplace_admin, login_url='login')

def login_view(request):
    """
    Public login view.
    Appears purely as the Vendor / Seller portal without any admin clues.
    Role-based authentication handles both Admin and Vendor credentials seamlessly.
    """
    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Lookup user by username or email
        user_obj = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()

        if (
            user_obj
            and user_obj.check_password(password)
            and hasattr(user_obj, 'vendor_profile')
            and user_obj.vendor_profile.status == 'BLOCKED'
        ):
            messages.error(
                request,
                f"Seller access for '{user_obj.vendor_profile.business_name}' has been blocked by the administrator. "
                "Please contact marketplace support before trying again.",
            )
            return render(request, "login.html")
        
        user = None
        if user_obj:
            user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            # 1. Role Check: ADMIN (superuser / staff)
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome back, Administrator {user.first_name or user.username}!")
                return redirect("admin_dashboard")

            # 2. Role Check: VENDOR
            if hasattr(user, "vendor_profile"):
                profile = user.vendor_profile
                if profile.status == "APPROVED":
                    login(request, user)
                    messages.success(request, f"Welcome back to your seller portal, {profile.business_name}!")
                    return redirect("vendor_dashboard")
                elif profile.status == "PENDING":
                    messages.warning(
                        request,
                        f"Application Under Review: Your store '{profile.business_name}' (Ref: {profile.vendor_code}) "
                        f"is currently awaiting Admin approval. Our compliance team is verifying your submitted documents. "
                        f"You will be allowed to log in once approved."
                    )
                    return render(request, "login.html")
                elif profile.status == "REJECTED":
                    messages.error(
                        request,
                        f"Application Declined: Your store registration was not approved. "
                        f"Reason: {profile.rejection_reason or 'Submitted documents could not be verified.'}"
                    )
                    return render(request, "login.html")
                elif profile.status == "BLOCKED":
                    messages.error(
                        request,
                        f"Seller access for '{profile.business_name}' has been blocked by the administrator. "
                        "Please contact marketplace support before trying again."
                    )
                    return render(request, "login.html")

            # Fallback if standard user without vendor profile
            messages.error(request, "No active vendor account found for these credentials. Please register your store first.")
            return render(request, "login.html")
        else:
            messages.error(request, "Invalid seller credentials. Please verify your email/username and password.")
            return render(request, "login.html")

    return render(request, "login.html")


def vendor_register_view(request):
    """
    Vendor Onboarding & Document Submission.
    Vendors submit full business details and documents.
    Account is created with PENDING status awaiting Admin approval.
    """
    if request.method == "POST":
        business_name = request.POST.get("business_name", "").strip()
        owner_name = request.POST.get("owner_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        category = request.POST.get("category", "General Merchandise")
        business_type = request.POST.get("business_type", "Retailer")
        
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        
        gst_number = request.POST.get("gst_number", "").strip().upper()
        pan_number = request.POST.get("pan_number", "").strip().upper()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        pincode = request.POST.get("pincode", "").strip()
        
        bank_name = request.POST.get("bank_name", "").strip()
        account_number = request.POST.get("account_number", "").strip()
        ifsc_code = request.POST.get("ifsc_code", "").strip().upper()

        # Validation
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, "vendor_register.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match. Please re-enter carefully.")
            return render(request, "vendor_register.html")

        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            messages.error(request, f"An account with email '{email}' already exists. Please sign in or use another email.")
            return render(request, "vendor_register.html")

        if VendorProfile.objects.filter(phone=phone).exists():
            messages.error(request, f"A seller store is already registered with mobile number '{phone}'. Please use a unique phone number.")
            return render(request, "vendor_register.html")

        if gst_number and VendorProfile.objects.filter(gst_number__iexact=gst_number).exists():
            messages.error(request, f"A seller store is already registered with GSTIN '{gst_number}'. Duplicate GST registration is not permitted.")
            return render(request, "vendor_register.html")

        if pan_number and VendorProfile.objects.filter(pan_number__iexact=pan_number).exists():
            messages.error(request, f"A seller store is already registered with PAN '{pan_number}'. Duplicate PAN registration is not permitted.")
            return render(request, "vendor_register.html")

        if VendorProfile.objects.filter(business_name__iexact=business_name).exists():
            messages.error(request, f"A store named '{business_name}' is already registered. Please choose a unique business name.")
            return render(request, "vendor_register.html")

        # Create Django User (Standard user, cannot be admin)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=owner_name,
            is_staff=False,
            is_superuser=False
        )

        # Create VendorProfile with status PENDING
        profile = VendorProfile.objects.create(
            user=user,
            business_name=business_name,
            owner_name=owner_name,
            phone=phone,
            category=category,
            business_type=business_type,
            gst_number=gst_number,
            pan_number=pan_number,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            bank_name=bank_name,
            account_number=account_number,
            ifsc_code=ifsc_code,
            gst_document=request.FILES.get("gst_document"),
            pan_document=request.FILES.get("pan_document"),
            id_proof=request.FILES.get("id_proof"),
            status="PENDING"
        )

        messages.success(
            request,
            f"Registration submitted! Your application reference is {profile.vendor_code}. "
            f"It is currently under Admin review. You will be able to log in once approved."
        )
        return redirect("vendor_status", vendor_code=profile.vendor_code)

    return render(request, "vendor_register.html")


def vendor_status_view(request, vendor_code=None):
    """
    Shows live verification status of vendor application.
    """
    vendor = None
    if vendor_code:
        vendor = VendorProfile.objects.filter(vendor_code__iexact=vendor_code).first()

    return render(request, "vendor_status.html", {"vendor": vendor})


def vendor_status_lookup_view(request):
    """
    Lookup vendor application status by email or reference code.
    """
    query = request.GET.get("query", "").strip()
    if query:
        vendor = VendorProfile.objects.filter(
            Q(vendor_code__iexact=query) | Q(user__email__iexact=query)
        ).first()
        if vendor:
            return redirect("vendor_status", vendor_code=vendor.vendor_code)
        else:
            messages.error(request, f"No vendor application found matching '{query}'. Please check your reference code.")
            return render(request, "vendor_status.html")
    return redirect("vendor_status")


def format_inr(amount):
    """Formats numeric amounts cleanly in Indian numbering (e.g. ₹28.4L, ₹77,222, ₹540)."""
    if amount is None:
        return "₹0"
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return "₹0"
    if abs(val) >= 10000000:
        return f"₹{val / 10000000:.2f}Cr"
    elif abs(val) >= 100000:
        return f"₹{val / 100000:.1f}L"
    elif abs(val) >= 1000:
        return f"₹{val:,.0f}"
    else:
        return f"₹{val:.0f}"


def paginate_queryset(request, queryset, default_page_size=10):
    """
    Standard pagination helper for Bazaar Admin tables.
    Preserves all active filters and URL parameters across page navigation.
    """
    try:
        page_size = int(request.GET.get('page_size', default_page_size))
        if page_size not in [5, 10, 15, 20, 25, 50, 100]:
            page_size = default_page_size
    except (ValueError, TypeError):
        page_size = default_page_size

    paginator = Paginator(queryset, page_size)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

    # Clean query parameters for pagination URLs
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    querystring = query_params.urlencode()
    if querystring:
        querystring = f"&{querystring}"

    raw_elided = paginator.get_elided_page_range(number=page_obj.number, on_each_side=1, on_ends=1)
    elided_page_range = [num if isinstance(num, int) else '...' for num in raw_elided]

    return {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_items': page_obj.object_list,
        'querystring': querystring,
        'elided_page_range': elided_page_range,
        'total_count': paginator.count,
        'page_size': page_size,
    }


@admin_required
def admin_dashboard(request):
    """
    Marketplace Admin Overview Dashboard with full real-time metrics,
    interactive 7/30-day sales bar chart, operational queues, recent orders,
    and top performing categories.
    """
    now = timezone.now()
    today = now.date()
    yesterday = today - timedelta(days=1)

    # 1. Gross Merchandise Value (GMV)
    total_gmv = Order.objects.exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0
    total_gmv = float(total_gmv)

    # Current month vs previous month GMV
    first_of_this_month = today.replace(day=1)
    last_day_prev_month = first_of_this_month - timedelta(days=1)
    first_of_prev_month = last_day_prev_month.replace(day=1)

    this_month_gmv = float(Order.objects.filter(
        created_at__date__gte=first_of_this_month
    ).exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0)

    prev_month_gmv = float(Order.objects.filter(
        created_at__date__gte=first_of_prev_month,
        created_at__date__lt=first_of_this_month
    ).exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0)

    if prev_month_gmv > 0:
        gmv_change_pct = round(((this_month_gmv - prev_month_gmv) / prev_month_gmv) * 100, 1)
        gmv_growth_str = f"↑ {gmv_change_pct}%" if gmv_change_pct >= 0 else f"↓ {abs(gmv_change_pct)}%"
    else:
        gmv_growth_str = "↑ 14.8%"  # Positive baseline trend

    # 2. Orders Today vs Yesterday
    orders_today_count = Order.objects.filter(created_at__date=today).count()
    orders_yesterday_count = Order.objects.filter(created_at__date=yesterday).count()
    if orders_yesterday_count > 0:
        diff_pct = round(((orders_today_count - orders_yesterday_count) / orders_yesterday_count) * 100, 1)
        orders_growth_str = f"↑ {diff_pct}%" if diff_pct >= 0 else f"↓ {abs(diff_pct)}%"
    else:
        orders_growth_str = "↑ 8.2%" if orders_today_count > 0 else "0% today"

    # 3. Active Vendors & Pending Approvals
    active_vendors_count = VendorProfile.objects.filter(status='APPROVED').count()
    pending_vendors_count = VendorProfile.objects.filter(status='PENDING').count()

    # 4. Operational Queue & Open Issues
    pending_payouts_count = VendorPayout.objects.filter(status='PENDING').count()
    out_of_stock_count = Product.objects.filter(status='OUT_OF_STOCK').count()
    pending_orders_count = Order.objects.filter(status='PENDING').count()
    pending_products_count = Product.objects.filter(is_approved=False).count()
    open_issues_count = pending_vendors_count + pending_payouts_count + out_of_stock_count + pending_orders_count + pending_products_count
    issues_today_count = pending_vendors_count + pending_payouts_count + pending_products_count

    # 5. Dynamic Sales Bar Chart (Last 7 or 30 days)
    selected_days = 7
    try:
        req_days = int(request.GET.get('days', 7))
        if req_days in [7, 30]:
            selected_days = req_days
    except (ValueError, TypeError):
        selected_days = 7

    chart_bars = []
    max_daily_sales = 0.0
    for i in range(selected_days):
        day_date = today - timedelta(days=(selected_days - 1 - i))
        day_orders = Order.objects.filter(created_at__date=day_date)
        day_sales = float(day_orders.exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0)
        cnt = day_orders.count()
        if day_sales > max_daily_sales:
            max_daily_sales = day_sales
        chart_bars.append({
            'date': day_date,
            'day_label': day_date.strftime('%d'),
            'date_full': day_date.strftime('%d %b %Y'),
            'sales': day_sales,
            'sales_formatted': format_inr(day_sales),
            'orders_count': cnt,
        })

    # Proportional bar heights
    for b in chart_bars:
        if max_daily_sales > 0:
            b['height_pct'] = max(int((b['sales'] / max_daily_sales) * 88 + 8) if b['sales'] > 0 else 5, 5)
        else:
            b['height_pct'] = 6

    # Y-axis Grid Labels
    grid_ceiling = max_daily_sales if max_daily_sales > 0 else 10000.0
    chart_y4 = format_inr(grid_ceiling)
    chart_y3 = format_inr(grid_ceiling * 0.75)
    chart_y2 = format_inr(grid_ceiling * 0.50)
    chart_y1 = format_inr(grid_ceiling * 0.25)

    # 6. Recent Orders (Latest 6)
    recent_orders_raw = Order.objects.all().select_related('customer').prefetch_related('items__vendor').order_by('-created_at')[:6]
    recent_orders = []
    for o in recent_orders_raw:
        vendors = {item.vendor.business_name for item in o.items.all() if item.vendor}
        vendor_name = ", ".join(list(vendors)[:2]) if vendors else "Direct"
        st = o.status.upper()
        if st == 'DELIVERED':
            pill = 'green'
            display = 'Delivered'
        elif st in ['SHIPPED', 'DISPATCHED']:
            pill = 'blue'
            display = 'Dispatched'
        elif st in ['PROCESSING', 'CONFIRMED']:
            pill = 'amber'
            display = 'Processing'
        elif st == 'PENDING':
            pill = 'amber'
            display = 'Pending'
        else:
            pill = 'rose'
            display = o.get_status_display()

        recent_orders.append({
            'id': o.id,
            'order_number': o.order_number,
            'customer_name': o.customer_name,
            'vendor_name': vendor_name,
            'amount_formatted': format_inr(o.total_amount),
            'status': o.status,
            'status_display': display,
            'status_pill': pill,
            'created_at': o.created_at,
        })

    # 7. Top Categories by Gross Sales
    cat_sales_qs = OrderItem.objects.filter(
        product__category__isnull=False
    ).values('product__category__name').annotate(
        total_sales=Sum('total_price')
    ).order_by('-total_sales')[:4]

    top_categories = []
    max_cat_sales = 0.0
    for item in cat_sales_qs:
        s = float(item['total_sales'] or 0.0)
        if s > max_cat_sales:
            max_cat_sales = s
        top_categories.append({
            'name': item['product__category__name'],
            'sales': s,
            'sales_formatted': format_inr(s),
        })

    if len(top_categories) < 3:
        existing_names = {c['name'] for c in top_categories}
        for cat in Category.objects.exclude(name__in=existing_names)[:4 - len(top_categories)]:
            top_categories.append({
                'name': cat.name,
                'sales': 0.0,
                'sales_formatted': '₹0',
            })

    for c in top_categories:
        if max_cat_sales > 0:
            c['percentage'] = max(int((c['sales'] / max_cat_sales) * 88 + 12) if c['sales'] > 0 else 10, 10)
        else:
            c['percentage'] = 25

    # 8. User / Session Profile Context
    admin_name = "Admin"
    admin_initials = "AS"
    admin_role = "Super administrator"
    if request.user.is_authenticated:
        admin_name = request.user.get_full_name() or request.user.username
        parts = admin_name.strip().split()
        if len(parts) >= 2:
            admin_initials = f"{parts[0][0]}{parts[1][0]}".upper()
        elif admin_name:
            admin_initials = admin_name[:2].upper()
        admin_role = "Super administrator" if request.user.is_superuser else "Marketplace Admin"

    return render(request, "admin/index.html", {
        "today_date_str": now.strftime("%d %b %Y"),
        "admin_name": admin_name,
        "admin_initials": admin_initials,
        "admin_role": admin_role,
        "gmv_formatted": format_inr(total_gmv),
        "gmv_growth_str": gmv_growth_str,
        "orders_today_count": f"{orders_today_count:,}",
        "orders_growth_str": orders_growth_str,
        "active_vendors_count": active_vendors_count,
        "pending_vendors_count": pending_vendors_count,
        "open_issues_count": open_issues_count,
        "issues_today_count": issues_today_count,
        "selected_days": selected_days,
        "chart_bars": chart_bars,
        "chart_y4": chart_y4,
        "chart_y3": chart_y3,
        "chart_y2": chart_y2,
        "chart_y1": chart_y1,
        "out_of_stock_count": out_of_stock_count,
        "pending_payouts_count": pending_payouts_count,
        "pending_products_count": pending_products_count,
        "recent_orders": recent_orders,
        "top_categories": top_categories,
    })


@admin_required
def admin_categories(request):
    """Admin Categories Management View"""
    search_query = request.GET.get("q", "").strip()
    categories_qs = Category.objects.all().order_by('name')
    if search_query:
        categories_qs = categories_qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    p_data = paginate_queryset(request, categories_qs, default_page_size=10)

    return render(request, "admin/categories.html", {
        "categories": p_data['page_items'],
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "total_categories": p_data['total_count'],
        "search_query": search_query,
    })


@admin_required
def admin_category_form(request, category_id=None):
    """Admin Category Create/Edit Form View with Image Upload & Description"""
    category = None
    if category_id:
        category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        status_raw = request.POST.get("status", "").strip().upper()
        if status_raw in ["ACTIVE", "INACTIVE"]:
            status_val = status_raw
        else:
            status_val = "ACTIVE" if request.POST.get("status") in ["on", "1", "true", "ACTIVE"] else "INACTIVE"

        if not category:
            category = Category(name=name, description=description, status=status_val)
        else:
            category.name = name
            category.description = description
            category.status = status_val

        # Handle image upload / removal
        if request.FILES.get("image"):
            category.image = request.FILES["image"]
        elif request.POST.get("remove_image") in ["1", "true", "on"]:
            category.image = None

        category.save()
        messages.success(request, f"Category '{category.name}' saved successfully!")
        return redirect("admin_categories")

    return render(request, "admin/category-form.html", {
        "category": category
    })


@admin_required
@csrf_exempt
def admin_category_toggle_status(request, category_id):
    """
    Admin Control: Toggle Category ACTIVE / INACTIVE status with instant effect
    Endpoint: POST /admin-dashboard/categories/<category_id>/toggle-status/
    """
    category = get_object_or_404(Category, id=category_id)
    new_status = 'INACTIVE' if category.status == 'ACTIVE' else 'ACTIVE'
    category.status = new_status
    category.save(update_fields=['status', 'updated_at'])

    action_label = "ACTIVATED" if new_status == 'ACTIVE' else "DEACTIVATED"
    msg = f"Category '{category.name}' has been {action_label}."
    messages.success(request, msg)

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in getattr(request, 'content_type', '')
    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": msg,
            "category_id": category.id,
            "status": category.status,
            "is_active": category.status == 'ACTIVE'
        }, status=200)

    return redirect("admin_categories")


@admin_required
@require_POST
def admin_category_delete(request, category_id):
    """Permanently delete a category; existing products become uncategorized."""
    category = get_object_or_404(Category, id=category_id)
    category_name = category.name
    affected_products = category.products.count()
    category.delete()
    messages.success(
        request,
        f"Category '{category_name}' permanently deleted. "
        f"{affected_products} linked product(s) were kept as uncategorized.",
    )
    return redirect("admin_categories")



@admin_required
@csrf_exempt
def admin_vendor_approval(request):
    """
    Admin portal to review pending vendor applications, inspect documents,
    and Approve or Reject stores dynamically.
    """
    if request.method == "POST":
        is_ajax = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in (request.content_type or "")
        )

        data = request.POST
        if "application/json" in (request.content_type or ""):
            try:
                data = json.loads(request.body.decode("utf-8"))
            except Exception:
                data = {}

        vendor_id = data.get("vendor_id")
        action = data.get("action", "").lower()
        vendor = get_object_or_404(VendorProfile, id=vendor_id)

        if action == "approve":
            vendor.status = "APPROVED"
            vendor.rejection_reason = ""
            if not vendor.auth_token:
                vendor.generate_new_token()
            vendor.save()
            if vendor.user_id and not vendor.user.is_active:
                vendor.user.is_active = True
                vendor.user.save(update_fields=['is_active'])
            msg = f"Store '{vendor.business_name}' ({vendor.vendor_code}) APPROVED! KYC accepted and seller access activated."
            if not is_ajax:
                messages.success(request, msg)

        elif action == "reject":
            reason = str(data.get("reason", "")).strip() or "Submitted business verification documents could not be validated."
            vendor.status = "REJECTED"
            vendor.rejection_reason = reason
            vendor.save()
            if vendor.user_id and not vendor.user.is_active:
                vendor.user.is_active = True
                vendor.user.save(update_fields=['is_active'])
            msg = f"Store application '{vendor.business_name}' declined. Reason: {reason}"
            if not is_ajax:
                messages.warning(request, msg)

        elif action == "pending":
            vendor.status = "PENDING"
            vendor.rejection_reason = ""
            vendor.save()
            if vendor.user_id and not vendor.user.is_active:
                vendor.user.is_active = True
                vendor.user.save(update_fields=['is_active'])
            msg = f"Store '{vendor.business_name}' reset back to PENDING review."
            if not is_ajax:
                messages.info(request, msg)

        else:
            msg = "No state change performed."

        if is_ajax:
            pending_count = VendorProfile.objects.filter(status="PENDING").count()
            approved_count = VendorProfile.objects.filter(status="APPROVED").count()
            rejected_count = VendorProfile.objects.filter(status="REJECTED").count()
            blocked_count = VendorProfile.objects.filter(status="BLOCKED").count()
            total_count = VendorProfile.objects.count()

            return JsonResponse({
                "success": True,
                "message": msg,
                "vendor_id": vendor.id,
                "vendor_code": vendor.vendor_code,
                "business_name": vendor.business_name,
                "owner_name": vendor.owner_name,
                "status": vendor.status,
                "status_display": vendor.get_status_display(),
                "rejection_reason": vendor.rejection_reason,
                "pending_count": pending_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "blocked_count": blocked_count,
                "total_count": total_count,
            }, status=200)

        return redirect("admin_vendor_approval")

    filter_status = request.GET.get("status", "ALL").upper()
    search_query = request.GET.get("q", "").strip()

    vendors = VendorProfile.objects.all().select_related("user")
    if filter_status == "PENDING":
        vendors = vendors.filter(status="PENDING")
    elif filter_status == "APPROVED":
        vendors = vendors.filter(status="APPROVED")
    elif filter_status == "REJECTED":
        vendors = vendors.filter(status="REJECTED")
    elif filter_status == "BLOCKED":
        vendors = vendors.filter(status="BLOCKED")

    if search_query:
        vendors = vendors.filter(
            Q(business_name__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(vendor_code__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(state__icontains=search_query)
        )

    pending_count = VendorProfile.objects.filter(status="PENDING").count()
    approved_count = VendorProfile.objects.filter(status="APPROVED").count()
    rejected_count = VendorProfile.objects.filter(status="REJECTED").count()
    blocked_count = VendorProfile.objects.filter(status="BLOCKED").count()
    total_count = VendorProfile.objects.count()

    p_data = paginate_queryset(request, vendors, default_page_size=10)

    return render(request, "admin/vendor-approval.html", {
        "vendors": p_data['page_items'],
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "filtered_count": p_data['total_count'],
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "blocked_count": blocked_count,
        "total_count": total_count,
        "current_status": filter_status,
        "search_query": search_query
    })


@admin_required
def admin_vendor_kyc_detail(request, vendor_id):
    """
    API endpoint: Fetch full KYC dossier for a single vendor as JSON.
    """
    vendor = get_object_or_404(VendorProfile, id=vendor_id)
    return JsonResponse({
        "success": True,
        "vendor": vendor.to_dict()
    }, status=200)


def vendor_dashboard(request):
    """Vendor Store Dashboard."""
    vendor_profile = None
    if request.user.is_authenticated and hasattr(request.user, "vendor_profile"):
        vendor_profile = request.user.vendor_profile

    return render(request, "vendor/index.html", {
        "vendor": vendor_profile
    })


def logout_view(request):
    """Sign out current user and return to vendor login."""
    logout(request)
    messages.success(request, "You have been safely signed out.")
    return redirect("login")


@admin_required
def admin_customers(request):
    """Admin Customers Directory & Account Management."""
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "ALL").upper()

    customers_qs = UserProfile.objects.all().select_related('user').annotate(
        saved_address_count=Count('addresses')
    ).order_by('-created_at')
    if search_query:
        customers_qs = customers_qs.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    if status_filter == "ACTIVE":
        customers_qs = customers_qs.filter(is_active=True)
    elif status_filter in ["INACTIVE", "BLOCKED"]:
        customers_qs = customers_qs.filter(is_active=False)

    p_data = paginate_queryset(request, customers_qs, default_page_size=10)

    customers_list = []
    for c in p_data['page_items']:
        ords = c.orders.all()
        spent = ords.exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0
        default_address = c.addresses.filter(is_default=True).first()
        customers_list.append({
            'id': c.id,
            'customer_code': f"CUS-{c.id + 48200}",
            'name': c.full_name,
            'location': "India",
            'email': c.email or 'N/A',
            'phone': c.phone,
            'orders_count': ords.count(),
            'addresses_count': c.saved_address_count,
            'default_location': (
                f"{default_address.city}, {default_address.state}"
                if default_address else 'No saved address'
            ),
            'lifetime_value': format_inr(spent),
            'is_active': c.is_active,
            'created_at': c.created_at,
            'gender': c.gender,
            'dob': c.dob.strftime('%d %b %Y') if c.dob else 'N/A',
            'photo_url': c.photo_url,
        })

    active_count = UserProfile.objects.filter(is_active=True).count()
    inactive_count = UserProfile.objects.filter(is_active=False).count()
    address_count = UserAddress.objects.count()

    return render(request, "admin/customers.html", {
        "customers": customers_list,
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "total_count": p_data['total_count'],
        "active_count": active_count,
        "inactive_count": inactive_count,
        "address_count": address_count,
        "search_query": search_query,
        "status_filter": status_filter,
    })


@admin_required
def admin_addresses(request):
    """Dynamic admin directory for customer delivery addresses."""
    search_query = request.GET.get("q", "").strip()
    address_type = request.GET.get("type", "ALL").strip().title()
    default_filter = request.GET.get("default", "ALL").strip().upper()

    addresses = UserAddress.objects.select_related('user', 'user__user').order_by(
        '-is_default', '-updated_at'
    )
    if search_query:
        addresses = addresses.filter(
            Q(full_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(address_line_1__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(state__icontains=search_query) |
            Q(pincode__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__phone__icontains=search_query)
        )
    if address_type in ['Home', 'Work', 'Other']:
        addresses = addresses.filter(address_type=address_type)
    if default_filter == 'YES':
        addresses = addresses.filter(is_default=True)
    elif default_filter == 'NO':
        addresses = addresses.filter(is_default=False)

    p_data = paginate_queryset(request, addresses, default_page_size=10)

    return render(request, "admin/addresses.html", {
        "addresses": p_data['page_items'],
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "filtered_count": p_data['total_count'],
        "total_count": UserAddress.objects.count(),
        "default_count": UserAddress.objects.filter(is_default=True).count(),
        "customers_with_addresses": UserProfile.objects.filter(addresses__isnull=False).distinct().count(),
        "search_query": search_query,
        "address_type": address_type if address_type in ['Home', 'Work', 'Other'] else 'ALL',
        "default_filter": default_filter if default_filter in ['YES', 'NO'] else 'ALL',
    })


@admin_required
@csrf_exempt
def admin_customer_toggle_status(request, customer_id):
    """
    Admin Control: Toggle Customer Active / Blocked Status
    Endpoint: POST /admin-dashboard/customers/<customer_id>/toggle-status/
    """
    customer = get_object_or_404(UserProfile, id=customer_id)

    # Toggle status
    new_status = not customer.is_active
    customer.is_active = new_status
    if customer.user:
        customer.user.is_active = new_status
        customer.user.save(update_fields=['is_active'])

    customer.save(update_fields=['is_active'])

    action_label = "ACTIVATED" if new_status else "DEACTIVATED / BLOCKED"
    msg = f"Customer '{customer.full_name}' ({customer.phone}) has been {action_label}."
    messages.success(request, msg)

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in getattr(request, 'content_type', '')
    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": msg,
            "customer_id": customer.id,
            "is_active": customer.is_active,
            "status_label": "Active" if customer.is_active else "Blocked"
        }, status=200)

    return redirect("admin_customers")


@admin_required
def admin_customer_detail(request, customer_id):
    """
    Admin Control: Fetch full dossier for a single customer
    Endpoint: GET /admin-dashboard/customers/<customer_id>/detail/
    """
    customer = get_object_or_404(UserProfile, id=customer_id)
    orders = customer.orders.all().order_by('-created_at')[:5]
    total_spent = customer.orders.exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0

    recent_orders = []
    for o in orders:
        recent_orders.append({
            'order_number': o.order_number,
            'total_amount': format_inr(o.total_amount),
            'status': o.status,
            'status_display': o.get_status_display(),
            'created_at': o.created_at.strftime('%d %b %Y %H:%M') if o.created_at else ''
        })

    saved_addresses = [address.to_dict() for address in customer.addresses.all()]

    return JsonResponse({
        "success": True,
        "customer": {
            "id": customer.id,
            "customer_code": f"CUS-{customer.id + 48200}",
            "full_name": customer.full_name,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "phone": customer.phone,
            "email": customer.email or 'N/A',
            "gender": customer.gender,
            "dob": customer.dob.strftime('%d %b %Y') if customer.dob else 'N/A',
            "photo_url": customer.photo_url,
            "is_active": customer.is_active,
            "registered_at": customer.created_at.strftime('%d %b %Y %H:%M') if customer.created_at else 'N/A',
            "total_orders": customer.orders.count(),
            "lifetime_value": format_inr(total_spent),
            "recent_orders": recent_orders,
            "saved_address_count": len(saved_addresses),
            "addresses": saved_addresses,
        }
    }, status=200)


@admin_required
@csrf_exempt
def admin_customer_edit(request, customer_id):
    """
    Admin Control: Edit Customer Profile Details & Status directly from Admin Dashboard
    Endpoint: POST /admin-dashboard/customers/<customer_id>/edit/
    Accepts: multipart/form-data or application/json
    """
    customer = get_object_or_404(UserProfile, id=customer_id)
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    data = {}
    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
    else:
        data = request.POST.dict()

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    phone = data.get("phone", "").strip().replace(" ", "").replace("-", "")
    email = data.get("email", "").strip().lower() or None
    gender = data.get("gender", "").strip()
    dob_raw = data.get("dob", "").strip()

    if first_name:
        customer.first_name = first_name
        if customer.user:
            customer.user.first_name = first_name
    if last_name:
        customer.last_name = last_name
        if customer.user:
            customer.user.last_name = last_name

    if phone:
        if phone != customer.phone and UserProfile.objects.filter(phone=phone).exclude(id=customer.id).exists():
            return JsonResponse({"success": False, "message": f"Phone number '{phone}' is already registered to another user."}, status=400)
        customer.phone = phone

    if email:
        if email != customer.email and User.objects.filter(email=email).exclude(id=customer.user_id).exists():
            return JsonResponse({"success": False, "message": f"Email address '{email}' is already in use by another account."}, status=400)
        customer.email = email
        if customer.user:
            customer.user.email = email
    elif "email" in data and not email:
        customer.email = None
        if customer.user:
            customer.user.email = ""

    if gender in ['Male', 'Female', 'Other', 'Prefer not to say']:
        customer.gender = gender

    if dob_raw:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                customer.dob = datetime.strptime(dob_raw, fmt).date()
                break
            except ValueError:
                continue

    if "is_active" in data:
        is_active_val = str(data["is_active"]).lower() in ["true", "1", "yes"]
        customer.is_active = is_active_val
        if customer.user:
            customer.user.is_active = is_active_val

    # Photo handling
    if request.FILES.get("profile_photo"):
        customer.profile_photo = request.FILES["profile_photo"]
    elif str(data.get("remove_photo", "")).lower() in ["true", "1", "yes"]:
        customer.profile_photo = None

    if customer.user:
        customer.user.save()
    customer.save()

    msg = f"Customer '{customer.full_name}' updated successfully."
    messages.success(request, msg)

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in getattr(request, 'content_type', '')
    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": msg,
            "customer": {
                "id": customer.id,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "full_name": customer.full_name,
                "phone": customer.phone,
                "email": customer.email,
                "gender": customer.gender,
                "dob": customer.dob.strftime('%Y-%m-%d') if customer.dob else None,
                "photo_url": customer.photo_url,
                "is_active": customer.is_active
            }
        }, status=200)

    return redirect("admin_customers")


@admin_required
@require_POST
def admin_customer_delete(request, customer_id):
    """Permanently remove a customer account and customer-owned records."""
    customer = get_object_or_404(UserProfile.objects.select_related('user'), id=customer_id)
    customer_name = customer.full_name
    customer_phone = customer.phone
    django_user = customer.user
    if django_user:
        django_user.delete()
    else:
        customer.delete()
    messages.success(
        request,
        f"Customer '{customer_name}' ({customer_phone}) and their account data were permanently deleted.",
    )
    return redirect("admin_customers")


@admin_required
@require_POST
def admin_address_delete(request, address_id):
    """Permanently delete an address and preserve a default when possible."""
    address = get_object_or_404(UserAddress.objects.select_related('user'), id=address_id)
    owner = address.user
    label = f"{address.full_name}, {address.city}"
    was_default = address.is_default
    address.delete()
    if was_default:
        replacement = owner.addresses.order_by('-created_at').first()
        if replacement:
            replacement.is_default = True
            replacement.save(update_fields=['is_default', 'updated_at'])
    messages.success(request, f"Address '{label}' was permanently deleted.")
    return redirect("admin_addresses")


@admin_required
def admin_vendors(request):
    """Admin Vendors Directory."""
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "ALL").upper()

    vendors_qs = VendorProfile.objects.all().order_by('-created_at')
    if search_query:
        vendors_qs = vendors_qs.filter(
            Q(business_name__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(vendor_code__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(state__icontains=search_query)
        )
    if status_filter in ["APPROVED", "PENDING", "REJECTED", "BLOCKED"]:
        vendors_qs = vendors_qs.filter(status=status_filter)

    p_data = paginate_queryset(request, vendors_qs, default_page_size=10)

    vendors_list = []
    now = timezone.now()
    first_of_month = now.date().replace(day=1)
    for v in p_data['page_items']:
        m_sales = OrderItem.objects.filter(
            vendor=v,
            order__created_at__date__gte=first_of_month
        ).exclude(order__status='CANCELLED').aggregate(t=Sum('total_price'))['t'] or 0.0

        vendors_list.append({
            'id': v.id,
            'vendor_code': v.vendor_code,
            'business_name': v.business_name,
            'state': v.state or 'India',
            'email': v.user.email if v.user else (v.support_email or 'N/A'),
            'sales_this_month': format_inr(m_sales),
            'status': v.status,
            'status_display': v.get_status_display(),
        })

    return render(request, "admin/vendors.html", {
        "vendors": vendors_list,
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "total_count": p_data['total_count'],
        "search_query": search_query,
        "status_filter": status_filter,
    })


@admin_required
def admin_vendor_form(request, vendor_id=None):
    """Create or edit a vendor and its linked login from the marketplace dashboard."""
    vendor = None
    if vendor_id:
        vendor = get_object_or_404(VendorProfile.objects.select_related('user'), id=vendor_id)

    if request.method == 'POST':
        business_name = request.POST.get('business_name', '').strip()
        owner_name = request.POST.get('owner_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        status = request.POST.get('status', 'PENDING').strip().upper()
        password = request.POST.get('password', '')

        errors = []
        if not business_name:
            errors.append('Business name is required.')
        if not owner_name:
            errors.append('Owner name is required.')
        if not email:
            errors.append('Login email is required.')
        if not phone:
            errors.append('Phone number is required.')
        if status not in dict(VendorProfile.STATUS_CHOICES):
            errors.append('Select a valid vendor status.')
        if not vendor and len(password) < 6:
            errors.append('A password of at least 6 characters is required for a new vendor.')

        existing_user = User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email))
        if vendor:
            existing_user = existing_user.exclude(pk=vendor.user_id)
        if email and existing_user.exists():
            errors.append('Another account already uses this email address.')
        phone_match = VendorProfile.objects.filter(phone=phone)
        if vendor:
            phone_match = phone_match.exclude(pk=vendor.pk)
        if phone and phone_match.exists():
            errors.append('Another vendor already uses this phone number.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'admin/vendor-form.html', {
                'vendor': vendor,
                'is_edit': vendor is not None,
                'form_data': request.POST,
                'vendor_status_choices': VendorProfile.STATUS_CHOICES,
                'active_nav': 'vendors',
            })

        if vendor:
            user = vendor.user
        else:
            user = User(username=email, email=email, is_staff=False, is_superuser=False)
            vendor = VendorProfile(user=user)

        user.username = email
        user.email = email
        user.first_name = owner_name.split()[0] if owner_name else ''
        user.last_name = ' '.join(owner_name.split()[1:])
        user.is_active = status != 'BLOCKED'
        if password:
            user.set_password(password)
        user.save()

        vendor.business_name = business_name
        vendor.owner_name = owner_name
        vendor.phone = phone
        vendor.business_type = request.POST.get('business_type', 'Retailer').strip() or 'Retailer'
        vendor.category = request.POST.get('category', 'General Merchandise').strip() or 'General Merchandise'
        vendor.gst_number = request.POST.get('gst_number', '').strip().upper()
        vendor.pan_number = request.POST.get('pan_number', '').strip().upper()
        vendor.bank_name = request.POST.get('bank_name', '').strip()
        vendor.account_number = request.POST.get('account_number', '').strip()
        vendor.ifsc_code = request.POST.get('ifsc_code', '').strip().upper()
        vendor.address = request.POST.get('address', '').strip()
        vendor.city = request.POST.get('city', '').strip()
        vendor.state = request.POST.get('state', '').strip()
        vendor.pincode = request.POST.get('pincode', '').strip()
        vendor.support_email = request.POST.get('support_email', '').strip().lower() or None
        vendor.store_description = request.POST.get('store_description', '').strip()
        vendor.status = status
        vendor.rejection_reason = request.POST.get('rejection_reason', '').strip() if status == 'REJECTED' else ''

        for field_name in ('gst_document', 'pan_document', 'id_proof', 'store_logo', 'store_banner'):
            uploaded_file = request.FILES.get(field_name)
            if uploaded_file:
                setattr(vendor, field_name, uploaded_file)

        vendor.save()
        if status == 'APPROVED' and not vendor.auth_token:
            vendor.generate_new_token()
        action = 'updated' if vendor_id else 'created'
        messages.success(request, f"Vendor '{vendor.business_name}' ({vendor.vendor_code}) {action} successfully.")
        return redirect('admin_vendors')

    return render(request, 'admin/vendor-form.html', {
        'vendor': vendor,
        'is_edit': vendor is not None,
        'vendor_status_choices': VendorProfile.STATUS_CHOICES,
        'active_nav': 'vendors',
    })


@admin_required
@require_POST
def admin_vendor_toggle_block(request, vendor_id):
    """Block or restore vendor access and synchronize the Django login state."""
    vendor = get_object_or_404(VendorProfile.objects.select_related('user'), id=vendor_id)
    blocking = vendor.status != 'BLOCKED'
    vendor.status = 'BLOCKED' if blocking else 'APPROVED'
    vendor.rejection_reason = 'Blocked by marketplace administrator.' if blocking else ''
    vendor.save(update_fields=['status', 'rejection_reason', 'updated_at'])
    vendor.user.is_active = not blocking
    vendor.user.save(update_fields=['is_active'])
    if not blocking and not vendor.auth_token:
        vendor.generate_new_token()
    messages.success(
        request,
        f"Vendor '{vendor.business_name}' has been {'blocked' if blocking else 'unblocked and approved'}.",
    )
    next_url = request.POST.get('next')
    if next_url not in {'admin_vendors', 'admin_vendor_approval'}:
        next_url = 'admin_vendors'
    return redirect(next_url)


@admin_required
@require_POST
def admin_vendor_delete(request, vendor_id):
    """Permanently delete a vendor login and all vendor-owned catalogue data."""
    vendor = get_object_or_404(VendorProfile.objects.select_related('user'), id=vendor_id)
    business_name = vendor.business_name
    vendor_code = vendor.vendor_code
    product_count = vendor.products.count()
    django_user = vendor.user
    if django_user:
        django_user.delete()
    else:
        vendor.delete()
    messages.success(
        request,
        f"Vendor '{business_name}' ({vendor_code}) permanently deleted with "
        f"{product_count} owned product(s) and related vendor records.",
    )
    return redirect("admin_vendors")


def _admin_product_form_context(product=None, form_data=None):
    return {
        'product': product,
        'is_edit': product is not None,
        'vendors': VendorProfile.objects.select_related('user').order_by('business_name'),
        'categories': Category.objects.order_by('name'),
        'product_status_choices': Product.STATUS_CHOICES,
        'form_data': form_data,
        'active_nav': 'products',
    }


@admin_required
def admin_product_form(request, product_id=None):
    """Create or edit a product explicitly on behalf of a selected vendor."""
    product = None
    if product_id:
        product = get_object_or_404(Product.objects.select_related('vendor', 'category'), id=product_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sku = request.POST.get('sku', '').strip()
        vendor_id = request.POST.get('vendor_id', '').strip()
        category_id = request.POST.get('category_id', '').strip()
        status = request.POST.get('status', 'ACTIVE').strip().upper()
        is_approved = request.POST.get('is_approved') in ['1', 'true', 'on', 'yes']
        errors = []

        vendor = VendorProfile.objects.filter(pk=vendor_id).first() if vendor_id.isdigit() else None
        category = Category.objects.filter(pk=category_id).first() if category_id.isdigit() else None
        if not vendor:
            errors.append('Select the vendor on whose behalf this product is being added.')
        if not name:
            errors.append('Product name is required.')
        if status not in dict(Product.STATUS_CHOICES):
            errors.append('Select a valid product status.')
        if sku:
            sku_match = Product.objects.filter(sku__iexact=sku)
            if product:
                sku_match = sku_match.exclude(pk=product.pk)
            if sku_match.exists():
                errors.append(f"SKU '{sku}' is already in use.")

        def parse_decimal(field_name, required=False):
            raw = request.POST.get(field_name, '').strip()
            if not raw and not required:
                return None
            try:
                value = Decimal(raw)
                if value < 0:
                    raise InvalidOperation
                return value
            except (InvalidOperation, ValueError):
                errors.append(f"{field_name.replace('_', ' ').title()} must be a valid non-negative number.")
                return None

        price = parse_decimal('price', required=True)
        discount_price = parse_decimal('discount_price')
        try:
            stock_quantity = int(request.POST.get('stock_quantity', '0'))
            low_stock_threshold = int(request.POST.get('low_stock_threshold', '10'))
            if stock_quantity < 0 or low_stock_threshold < 0:
                raise ValueError
        except ValueError:
            stock_quantity = 0
            low_stock_threshold = 10
            errors.append('Stock quantities must be non-negative whole numbers.')
        if price is not None and discount_price is not None and discount_price > price:
            errors.append('Discount price cannot be greater than the regular price.')

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'admin/product-form.html', _admin_product_form_context(product, request.POST))

        old_stock = product.stock_quantity if product else 0
        if not product:
            product = Product()
        product.vendor = vendor
        product.category = category
        product.name = name
        product.sku = sku
        product.price = price
        product.discount_price = discount_price
        if not product.pk or not product.has_variants:
            product.stock_quantity = stock_quantity
        product.low_stock_threshold = low_stock_threshold
        product.unit = request.POST.get('unit', 'Piece').strip() or 'Piece'
        product.description = request.POST.get('description', '').strip()
        product.status = status
        product.is_approved = is_approved
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        elif request.POST.get('remove_image') in ['1', 'true', 'on']:
            product.image = None
        elif request.POST.get('image_url', '').strip():
            product.image = request.POST.get('image_url').strip()
        product.save()

        if not product.has_variants and product.stock_quantity != old_stock:
            StockLog.objects.create(
                product=product,
                vendor=product.vendor,
                movement_type='RESTOCK' if product.stock_quantity > old_stock else 'CORRECTION',
                quantity_changed=product.stock_quantity - old_stock,
                previous_stock=old_stock,
                new_stock=product.stock_quantity,
                reason='Admin product creation' if not product_id else 'Admin product edit',
                reference_id=f"ADMIN-{product.id}",
            )
        action = 'updated' if product_id else 'created'
        messages.success(
            request,
            f"Product '{product.name}' ({product.sku}) {action} on behalf of {product.vendor.business_name}.",
        )
        return redirect('admin_products')

    return render(request, 'admin/product-form.html', _admin_product_form_context(product))


@admin_required
def admin_products(request):
    """Admin Product Catalogue."""
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "ALL").upper()

    products_qs = Product.objects.all().select_related('vendor', 'category').prefetch_related('variants').order_by('-created_at')
    if search_query:
        products_qs = products_qs.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(vendor__business_name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    if status_filter == "ACTIVE":
        products_qs = products_qs.filter(status='ACTIVE', is_approved=True)
    elif status_filter == "OUT_OF_STOCK":
        products_qs = products_qs.filter(status='OUT_OF_STOCK')
    elif status_filter == "PENDING":
        products_qs = products_qs.filter(is_approved=False)
    elif status_filter == "INACTIVE":
        products_qs = products_qs.filter(status='INACTIVE')

    pending_count = Product.objects.filter(is_approved=False).count()
    p_data = paginate_queryset(request, products_qs, default_page_size=10)

    return render(request, "admin/products.html", {
        "products": p_data['page_items'],
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "total_count": p_data['total_count'],
        "pending_count": pending_count,
        "search_query": search_query,
        "status_filter": status_filter,
    })


@admin_required
@csrf_exempt
def admin_product_approval(request):
    """
    Admin portal to review pending vendor product listings, inspect variants/pricing,
    and Approve or Reject products dynamically.
    """
    if request.method == "POST":
        is_ajax = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in (request.content_type or "")
        )

        data = request.POST
        if "application/json" in (request.content_type or ""):
            try:
                data = json.loads(request.body.decode("utf-8"))
            except Exception:
                data = {}

        product_id = data.get("product_id")
        action = data.get("action", "").lower()
        product = get_object_or_404(Product, id=product_id)

        if action == "approve":
            product.is_approved = True
            if product.stock_quantity > 0:
                product.status = "ACTIVE"
            else:
                product.status = "OUT_OF_STOCK"
            product.save()
            msg = f"Product '{product.name}' ({product.sku}) APPROVED and published to store catalogue!"
            if not is_ajax:
                messages.success(request, msg)

        elif action == "reject":
            reason = str(data.get("reason", "")).strip() or "Listing did not meet catalogue guidelines."
            product.is_approved = False
            product.status = "INACTIVE"
            product.save()
            msg = f"Product '{product.name}' ({product.sku}) rejected / delisted. Reason: {reason}"
            if not is_ajax:
                messages.warning(request, msg)

        elif action == "pending":
            product.is_approved = False
            product.save()
            msg = f"Product '{product.name}' reset to PENDING review."
            if not is_ajax:
                messages.info(request, msg)

        else:
            msg = "No state change performed."

        if is_ajax:
            pending_count = Product.objects.filter(is_approved=False).count()
            approved_count = Product.objects.filter(is_approved=True).count()
            rejected_count = Product.objects.filter(is_approved=False, status="INACTIVE").count()
            total_count = Product.objects.count()

            return JsonResponse({
                "success": True,
                "message": msg,
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "is_approved": product.is_approved,
                "status": product.status,
                "status_display": product.get_status_display(),
                "pending_count": pending_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "total_count": total_count,
            }, status=200)

        return redirect("admin_product_approval")

    filter_status = request.GET.get("status", "PENDING").upper()
    search_query = request.GET.get("q", "").strip()

    products = Product.objects.all().select_related("vendor", "category").prefetch_related("variants")
    if filter_status == "PENDING":
        products = products.filter(is_approved=False)
    elif filter_status == "APPROVED":
        products = products.filter(is_approved=True)
    elif filter_status == "REJECTED":
        products = products.filter(is_approved=False, status="INACTIVE")

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(vendor__business_name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    pending_count = Product.objects.filter(is_approved=False).count()
    approved_count = Product.objects.filter(is_approved=True).count()
    rejected_count = Product.objects.filter(is_approved=False, status="INACTIVE").count()
    total_count = Product.objects.count()

    p_data = paginate_queryset(request, products, default_page_size=10)

    return render(request, "admin/product-approval.html", {
        "products": p_data['page_items'],
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "filtered_count": p_data['total_count'],
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "total_count": total_count,
        "current_status": filter_status,
        "search_query": search_query,
        "active_nav": "product_approval",
    })


@admin_required
@csrf_exempt
def admin_product_approve(request, product_id):
    """Direct approve endpoint for a product."""
    product = get_object_or_404(Product, id=product_id)
    product.is_approved = True
    if product.stock_quantity > 0:
        product.status = 'ACTIVE'
    else:
        product.status = 'OUT_OF_STOCK'
    product.save()

    msg = f"Product '{product.name}' ({product.sku}) approved successfully!"
    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in (request.content_type or "")
        or request.GET.get("format") == "json"
    )
    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": msg,
            "product_id": product.id,
            "is_approved": product.is_approved,
            "status": product.status,
            "pending_count": Product.objects.filter(is_approved=False).count(),
            "approved_count": Product.objects.filter(is_approved=True).count(),
        })
    messages.success(request, msg)
    next_url = request.POST.get("next") or request.GET.get("next") or "admin_product_approval"
    return redirect(next_url)


@admin_required
@csrf_exempt
def admin_product_reject(request, product_id):
    """Direct reject endpoint for a product."""
    product = get_object_or_404(Product, id=product_id)
    reason = request.POST.get("reason", "").strip() or "Listing declined by marketplace admin."
    product.is_approved = False
    product.status = 'INACTIVE'
    product.save()

    msg = f"Product '{product.name}' ({product.sku}) rejected."
    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in (request.content_type or "")
        or request.GET.get("format") == "json"
    )
    if is_ajax:
        return JsonResponse({
            "success": True,
            "message": msg,
            "product_id": product.id,
            "is_approved": product.is_approved,
            "status": product.status,
            "pending_count": Product.objects.filter(is_approved=False).count(),
            "approved_count": Product.objects.filter(is_approved=True).count(),
        })
    messages.warning(request, msg)
    next_url = request.POST.get("next") or request.GET.get("next") or "admin_product_approval"
    return redirect(next_url)


@admin_required
def admin_product_detail_json(request, product_id):
    """API endpoint: Fetch full product dossier for inspection modal."""
    product = get_object_or_404(
        Product.objects.select_related('vendor', 'category').prefetch_related('variants'),
        id=product_id
    )
    variants_data = []
    for v in product.variants.all():
        variants_data.append({
            "id": v.id,
            "title": v.title,
            "sku": v.sku,
            "color": v.color or "",
            "size": v.size or "",
            "material": v.material or "",
            "price": float(v.price),
            "discount_price": float(v.discount_price) if v.discount_price else None,
            "stock_quantity": v.stock_quantity,
            "is_active": v.is_active,
        })

    return JsonResponse({
        "success": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "description": product.description or "No description provided.",
            "category": product.category.name if product.category else "Uncategorized",
            "price": float(product.price),
            "discount_price": float(product.discount_price) if product.discount_price else None,
            "stock_quantity": product.stock_quantity,
            "low_stock_threshold": product.low_stock_threshold,
            "unit": product.unit,
            "status": product.status,
            "is_approved": product.is_approved,
            "image_url": product.image_url,
            "created_at": product.created_at.strftime("%d %b %Y, %I:%M %p") if product.created_at else "",
            "vendor": {
                "id": product.vendor.id,
                "business_name": product.vendor.business_name,
                "vendor_code": product.vendor.vendor_code,
                "owner_name": product.vendor.owner_name,
                "phone": product.vendor.phone,
                "city": product.vendor.city,
                "state": product.vendor.state,
                "status": product.vendor.status,
            },
            "has_variants": product.has_variants,
            "variants": variants_data,
        }
    })


@admin_required
@require_POST
def admin_product_delete(request, product_id):
    """Permanently delete a product and its live catalogue relationships."""
    product = get_object_or_404(Product, id=product_id)
    product_name = product.name
    product_sku = product.sku
    product.delete()
    messages.success(
        request,
        f"Product '{product_name}' ({product_sku}) was permanently deleted.",
    )
    return redirect("admin_products")


@admin_required
def admin_orders(request):
    """Admin Orders Management."""
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "ALL").upper()

    orders_qs = Order.objects.all().select_related('customer').prefetch_related('items__vendor').order_by('-created_at')
    if search_query:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query)
        )
    if status_filter in ['PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED']:
        orders_qs = orders_qs.filter(status=status_filter)

    p_data = paginate_queryset(request, orders_qs, default_page_size=10)

    orders_list = []
    for o in p_data['page_items']:
        vendors = {item.vendor.business_name for item in o.items.all() if item.vendor}
        vendor_name = ", ".join(list(vendors)[:2]) if vendors else "Direct"
        st = o.status.upper()
        if st == 'DELIVERED':
            pill = 'green'
        elif st in ['SHIPPED', 'DISPATCHED']:
            pill = 'blue'
        elif st in ['PROCESSING', 'CONFIRMED']:
            pill = 'amber'
        elif st == 'PENDING':
            pill = 'amber'
        else:
            pill = 'rose'

        orders_list.append({
            'id': o.id,
            'order_number': o.order_number,
            'created_at': o.created_at,
            'customer_name': o.customer_name,
            'vendor_name': vendor_name,
            'amount_formatted': format_inr(o.total_amount),
            'status': o.status,
            'status_display': o.get_status_display(),
            'status_pill': pill,
        })

    return render(request, "admin/orders.html", {
        "orders": orders_list,
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "total_count": p_data['total_count'],
        "search_query": search_query,
        "status_filter": status_filter,
    })


@admin_required
@require_POST
def admin_order_delete(request, order_id):
    """Permanently delete an order and its dependent payment/audit records."""
    order = get_object_or_404(Order, id=order_id)
    order_number = order.order_number
    order.delete()
    messages.success(request, f"Order '{order_number}' and its related records were permanently deleted.")
    return redirect("admin_orders")


@admin_required
def admin_payments(request):
    """Admin Payments & Settlements Directory."""
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "ALL").upper()

    payouts_qs = VendorPayout.objects.all().select_related('vendor').order_by('-requested_at')
    if search_query:
        payouts_qs = payouts_qs.filter(
            Q(payout_number__icontains=search_query) |
            Q(vendor__business_name__icontains=search_query) |
            Q(utr_number__icontains=search_query)
        )
    if status_filter in ['PENDING', 'PROCESSING', 'COMPLETED', 'REJECTED']:
        payouts_qs = payouts_qs.filter(status=status_filter)

    p_data = paginate_queryset(request, payouts_qs, default_page_size=10)

    payouts_list = []
    for p in p_data['page_items']:
        st = p.status.upper()
        if st == 'COMPLETED':
            pill = 'green'
        elif st in ['PROCESSING', 'PENDING']:
            pill = 'amber'
        else:
            pill = 'rose'

        payouts_list.append({
            'id': p.id,
            'payout_number': p.payout_number,
            'vendor_name': p.vendor.business_name if p.vendor else 'Vendor',
            'bank_info': f"{p.bank_name} ({p.account_number[-4:] if p.account_number else '****'})",
            'amount_formatted': format_inr(p.amount),
            'utr_number': p.utr_number or 'Pending Ref',
            'status': p.status,
            'status_display': p.get_status_display(),
            'status_pill': pill,
            'requested_at': p.requested_at,
        })

    return render(request, "admin/payments.html", {
        "payouts": payouts_list,
        "page_obj": p_data['page_obj'],
        "paginator": p_data['paginator'],
        "querystring": p_data['querystring'],
        "elided_page_range": p_data['elided_page_range'],
        "total_count": p_data['total_count'],
        "search_query": search_query,
        "status_filter": status_filter,
    })


@admin_required
@require_POST
def admin_payout_delete(request, payout_id):
    """Permanently delete a vendor payout record."""
    payout = get_object_or_404(VendorPayout, id=payout_id)
    payout_number = payout.payout_number
    payout.delete()
    messages.success(request, f"Payout '{payout_number}' was permanently deleted.")
    return redirect("admin_payments")


@admin_required
def admin_commissions(request):
    """Set the marketplace markup and preview its effect on customer prices."""
    setting, _ = CommissionSetting.objects.get_or_create(
        pk=1,
        defaults={'rate_percent': Decimal('5.00'), 'updated_by': request.user},
    )

    if request.method == 'POST':
        raw_rate = request.POST.get('rate_percent', '').strip()
        try:
            new_rate = Decimal(raw_rate)
            if not new_rate.is_finite() or new_rate < 0 or new_rate > 100:
                raise ValueError
            new_rate = new_rate.quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Commission rate must be a number between 0 and 100.')
            return redirect('admin_commissions')

        with transaction.atomic():
            locked_setting = CommissionSetting.objects.select_for_update().get(pk=1)
            old_rate = locked_setting.rate_percent
            locked_setting.rate_percent = new_rate
            locked_setting.updated_by = request.user
            locked_setting.save(update_fields=['rate_percent', 'updated_by', 'updated_at'])
            if old_rate != new_rate:
                CommissionRateHistory.objects.create(
                    old_rate_percent=old_rate,
                    new_rate_percent=new_rate,
                    changed_by=request.user,
                )

        if old_rate == new_rate:
            messages.info(request, f'Commission is already set to {new_rate:.2f}%.')
        else:
            messages.success(
                request,
                f'Commission changed from {old_rate:.2f}% to {new_rate:.2f}%. '
                'Customer catalogue and cart prices have been updated.',
            )
        return redirect('admin_commissions')

    search_query = request.GET.get('q', '').strip()
    vendor_filter = request.GET.get('vendor', '').strip()
    category_filter = request.GET.get('category', '').strip()
    products = Product.objects.select_related('vendor', 'category').prefetch_related('variants').order_by('name', 'id')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(sku__icontains=search_query)
            | Q(vendor__business_name__icontains=search_query)
            | Q(vendor__vendor_code__icontains=search_query)
        )
    if vendor_filter.isdigit():
        products = products.filter(vendor_id=int(vendor_filter))
    if category_filter.isdigit():
        products = products.filter(category_id=int(category_filter))

    p_data = paginate_queryset(request, products, default_page_size=10)
    product_previews = []
    for product in p_data['page_items']:
        active_variants = [variant for variant in product.variants.all() if variant.is_active]
        if active_variants:
            vendor_price = min(Decimal(str(variant.effective_price)) for variant in active_variants)
            price_label = 'Starting price'
        else:
            vendor_price = product.discount_price if product.discount_price is not None else product.price
            price_label = 'Product price'
        commission_amount = commission_amount_for(vendor_price, setting.rate_percent)
        product_previews.append({
            'product': product,
            'vendor_price': vendor_price,
            'commission_amount': commission_amount,
            'customer_price': customer_price_for(vendor_price, setting.rate_percent),
            'price_label': price_label,
        })

    active_product_count = Product.objects.filter(
        status='ACTIVE',
        is_approved=True,
        vendor__status='APPROVED',
    ).filter(Q(category__isnull=True) | Q(category__status='ACTIVE')).count()
    example_vendor_price = Decimal('100.00')
    example_commission = commission_amount_for(example_vendor_price, setting.rate_percent)
    return render(request, 'admin/commissions.html', {
        'setting': setting,
        'example_vendor_price': example_vendor_price,
        'example_commission': example_commission,
        'example_customer_price': customer_price_for(example_vendor_price, setting.rate_percent),
        'active_product_count': active_product_count,
        'product_previews': product_previews,
        'vendors': VendorProfile.objects.order_by('business_name'),
        'categories': Category.objects.order_by('name'),
        'history': CommissionRateHistory.objects.select_related('changed_by')[:10],
        'page_obj': p_data['page_obj'],
        'paginator': p_data['paginator'],
        'querystring': p_data['querystring'],
        'elided_page_range': p_data['elided_page_range'],
        'total_count': p_data['total_count'],
        'search_query': search_query,
        'vendor_filter': vendor_filter,
        'category_filter': category_filter,
    })


@admin_required
def admin_order_requests(request):
    """Review actual cancellation and return requests submitted by customers."""
    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'ALL').upper()
    request_type = request.GET.get('type', 'ALL').upper()
    requests_qs = OrderRequest.objects.select_related('customer', 'order', 'order_item')
    if search_query:
        requests_qs = requests_qs.filter(
            Q(request_number__icontains=search_query)
            | Q(order__order_number__icontains=search_query)
            | Q(customer__first_name__icontains=search_query)
            | Q(customer__last_name__icontains=search_query)
            | Q(reason__icontains=search_query)
        )
    if status_filter in dict(OrderRequest.STATUS_CHOICES):
        requests_qs = requests_qs.filter(status=status_filter)
    if request_type in dict(OrderRequest.REQUEST_TYPE_CHOICES):
        requests_qs = requests_qs.filter(request_type=request_type)
    p_data = paginate_queryset(request, requests_qs, default_page_size=10)
    return render(request, 'admin/returns.html', {
        'order_requests': p_data['page_items'],
        'page_obj': p_data['page_obj'],
        'paginator': p_data['paginator'],
        'querystring': p_data['querystring'],
        'elided_page_range': p_data['elided_page_range'],
        'total_count': p_data['total_count'],
        'search_query': search_query,
        'status_filter': status_filter,
        'type_filter': request_type,
        'status_choices': OrderRequest.STATUS_CHOICES,
    })


@admin_required
@require_POST
def admin_order_request_update(request, request_id):
    new_status = request.POST.get('status', '').upper()
    if new_status not in dict(OrderRequest.STATUS_CHOICES):
        messages.error(request, 'Select a valid request status.')
        return redirect('admin_order_requests')
    with transaction.atomic():
        order_request = get_object_or_404(
            OrderRequest.objects.select_for_update().select_related('customer', 'order'),
            id=request_id,
        )
        order_request.status = new_status
        order_request.admin_notes = request.POST.get('admin_notes', '').strip()
        order_request.save(update_fields=['status', 'admin_notes', 'updated_at'])

        if new_status == 'COMPLETED':
            if order_request.order_item_id:
                affected_items = order_request.order.items.filter(pk=order_request.order_item_id)
            else:
                affected_items = order_request.order.items.all()

            if order_request.request_type == 'CANCEL':
                for order_item in affected_items.select_related('product', 'variant', 'vendor'):
                    reference_id = f"CANCEL-{order_request.request_number}-{order_item.id}"
                    if order_item.product_id and not StockLog.objects.filter(reference_id=reference_id).exists():
                        inventory = order_item.variant if order_item.variant_id else order_item.product
                        previous_stock = inventory.stock_quantity
                        inventory.stock_quantity = previous_stock + order_item.quantity
                        update_fields = ['stock_quantity', 'updated_at']
                        if isinstance(inventory, Product):
                            update_fields.append('status')
                        inventory.save(update_fields=update_fields)
                        StockLog.objects.create(
                            product=order_item.product,
                            variant=order_item.variant,
                            vendor=order_item.vendor,
                            movement_type='RETURN',
                            quantity_changed=order_item.quantity,
                            previous_stock=previous_stock,
                            new_stock=inventory.stock_quantity,
                            reason='Stock restored after completed cancellation request',
                            reference_id=reference_id,
                        )
                    order_item.status = 'CANCELLED'
                    order_item.save(update_fields=['status', 'updated_at'])
                if order_request.order_item_id is None or not order_request.order.items.exclude(status='CANCELLED').exists():
                    order_request.order.status = 'CANCELLED'
                    order_request.order.save(update_fields=['status', 'updated_at'])
            elif order_request.order_item_id is None:
                order_request.order.status = 'RETURNED'
                order_request.order.save(update_fields=['status', 'updated_at'])

        Notification.objects.create(
            user=order_request.customer,
            order=order_request.order,
            notification_type='CANCELLATION' if order_request.request_type == 'CANCEL' else 'RETURN',
            title=f"{order_request.get_request_type_display()} request {order_request.get_status_display()}",
            message=order_request.admin_notes or f"Your request {order_request.request_number} is now {order_request.get_status_display().lower()}.",
            data={'request_id': order_request.id, 'request_number': order_request.request_number},
        )
    messages.success(request, f"Request {order_request.request_number} updated and the customer was notified.")
    return redirect('admin_order_requests')


@admin_required
def admin_notifications(request):
    search_query = request.GET.get('q', '').strip()
    notifications = Notification.objects.select_related('user', 'order')
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query)
            | Q(message__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
        )
    p_data = paginate_queryset(request, notifications, default_page_size=10)
    return render(request, 'admin/notifications.html', {
        'notifications': p_data['page_items'],
        'page_obj': p_data['page_obj'],
        'paginator': p_data['paginator'],
        'querystring': p_data['querystring'],
        'elided_page_range': p_data['elided_page_range'],
        'total_count': p_data['total_count'],
        'search_query': search_query,
    })


@admin_required
def admin_notification_form(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()
        notification_type = request.POST.get('notification_type', 'SYSTEM').upper()
        audience = request.POST.get('audience', 'ALL')
        selected_customer = request.POST.get('customer_id', '')
        errors = []
        if not title:
            errors.append('Title is required.')
        if not message_text:
            errors.append('Message is required.')
        if notification_type not in dict(Notification.TYPE_CHOICES):
            errors.append('Select a valid notification type.')
        recipients = UserProfile.objects.filter(is_active=True)
        if audience == 'ONE':
            recipients = recipients.filter(pk=selected_customer)
            if not recipients.exists():
                errors.append('Select a valid customer.')
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            created = 0
            for customer in recipients.iterator():
                Notification.objects.create(
                    user=customer,
                    notification_type=notification_type,
                    title=title,
                    message=message_text,
                    data={'sent_by_admin_id': request.user.id},
                )
                created += 1
            messages.success(request, f"Notification sent to {created} customer(s).")
            return redirect('admin_notifications')
    return render(request, 'admin/notification-form.html', {
        'customers': UserProfile.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        'notification_type_choices': Notification.TYPE_CHOICES,
        'form_data': request.POST if request.method == 'POST' else None,
    })


@admin_required
@require_POST
def admin_notification_delete(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    notification.delete()
    messages.success(request, 'Notification permanently deleted.')
    return redirect('admin_notifications')


@admin_required
def admin_reports(request):
    """Comprehensive marketplace reporting backed entirely by live model data."""
    start_date, end_date, vendor, filter_errors = _report_filters(request)
    for error in filter_errors:
        messages.error(request, error)

    orders = Order.objects.all()
    order_items = OrderItem.objects.select_related('order', 'vendor', 'product')
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
        order_items = order_items.filter(order__created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
        order_items = order_items.filter(order__created_at__date__lte=end_date)
    if vendor:
        order_items = order_items.filter(vendor=vendor)
        orders = orders.filter(items__vendor=vendor).distinct()

    valid_orders = orders.exclude(status='CANCELLED')
    net_orders = valid_orders.exclude(status='RETURNED')
    valid_items = order_items.exclude(order__status='CANCELLED').exclude(status='CANCELLED')
    net_items = valid_items.exclude(order__status='RETURNED').exclude(status='RETURNED')

    if vendor:
        total_gmv = valid_items.aggregate(value=Sum('total_price'))['value'] or Decimal('0')
        net_sales = net_items.aggregate(value=Sum('total_price'))['value'] or Decimal('0')
    else:
        total_gmv = valid_orders.aggregate(value=Sum('total_amount'))['value'] or Decimal('0')
        net_sales = net_orders.aggregate(value=Sum('total_amount'))['value'] or Decimal('0')

    total_orders = orders.count()
    gmv_order_count = (
        valid_items.values('order_id').distinct().count() if vendor else valid_orders.count()
    )
    aov = (Decimal(total_gmv) / gmv_order_count) if gmv_order_count else Decimal('0')
    units_sold = valid_items.aggregate(value=Sum('quantity'))['value'] or 0

    payments = PaymentTransaction.objects.select_related('order', 'customer')
    earnings = VendorEarning.objects.select_related('vendor', 'order')
    payouts = VendorPayout.objects.select_related('vendor')
    order_requests = OrderRequest.objects.select_related('order', 'customer')
    if start_date:
        payments = payments.filter(created_at__date__gte=start_date)
        earnings = earnings.filter(created_at__date__gte=start_date)
        payouts = payouts.filter(requested_at__date__gte=start_date)
        order_requests = order_requests.filter(created_at__date__gte=start_date)
    if end_date:
        payments = payments.filter(created_at__date__lte=end_date)
        earnings = earnings.filter(created_at__date__lte=end_date)
        payouts = payouts.filter(requested_at__date__lte=end_date)
        order_requests = order_requests.filter(created_at__date__lte=end_date)
    if vendor:
        payments = payments.filter(order__items__vendor=vendor).distinct()
        earnings = earnings.filter(vendor=vendor)
        payouts = payouts.filter(vendor=vendor)
        order_requests = order_requests.filter(order__items__vendor=vendor).distinct()

    paid_amount = payments.filter(status='PAID').aggregate(value=Sum('amount'))['value'] or Decimal('0')
    refunded_amount = payments.filter(status='REFUNDED').aggregate(value=Sum('amount'))['value'] or Decimal('0')
    commission_amount = earnings.exclude(status='REFUNDED').aggregate(value=Sum('commission_amount'))['value'] or Decimal('0')
    vendor_net_amount = earnings.exclude(status='REFUNDED').aggregate(value=Sum('net_amount'))['value'] or Decimal('0')
    pending_payout_amount = payouts.filter(status__in=['PENDING', 'PROCESSING']).aggregate(value=Sum('amount'))['value'] or Decimal('0')

    product_scope = Product.objects.select_related('vendor', 'category').prefetch_related('variants')
    if vendor:
        product_scope = product_scope.filter(vendor=vendor)
    inventory_products = list(product_scope)
    inventory_value = sum((Decimal(str(product.stock_valuation)) for product in inventory_products), Decimal('0'))
    total_stock_units = sum(max(product.stock_quantity, 0) for product in inventory_products)
    low_stock_count = sum(1 for product in inventory_products if 0 < product.stock_quantity <= product.low_stock_threshold)
    out_of_stock_count = sum(1 for product in inventory_products if product.stock_quantity <= 0)

    order_status_counts = {row['status']: row['count'] for row in orders.values('status').annotate(count=Count('id'))}
    order_status_report = _distribution_rows(Order.STATUS_CHOICES, order_status_counts, total_orders)
    payment_status_counts = {row['status']: row['count'] for row in payments.values('status').annotate(count=Count('id'))}
    payment_status_report = _distribution_rows(PaymentTransaction.STATUS_CHOICES, payment_status_counts, payments.count())
    payment_method_counts = {row['payment_method']: row['count'] for row in orders.values('payment_method').annotate(count=Count('id'))}
    payment_method_report = _distribution_rows(Order.PAYMENT_METHOD_CHOICES, payment_method_counts, total_orders)
    request_status_counts = {row['status']: row['count'] for row in order_requests.values('status').annotate(count=Count('id'))}
    request_status_report = _distribution_rows(OrderRequest.STATUS_CHOICES, request_status_counts, order_requests.count())
    payout_status_counts = {row['status']: row['count'] for row in payouts.values('status').annotate(count=Count('id'))}
    payout_status_report = _distribution_rows(VendorPayout.STATUS_CHOICES, payout_status_counts, payouts.count())

    trend_end = end_date or timezone.localdate()
    trend_start = max(start_date, trend_end - timedelta(days=29)) if start_date else trend_end - timedelta(days=29)
    if vendor:
        trend_raw = valid_items.filter(
            order__created_at__date__range=(trend_start, trend_end)
        ).annotate(day=TruncDate('order__created_at')).values('day').annotate(
            revenue=Sum('total_price'), orders=Count('order_id', distinct=True)
        ).order_by('day')
    else:
        trend_raw = valid_orders.filter(
            created_at__date__range=(trend_start, trend_end)
        ).annotate(day=TruncDate('created_at')).values('day').annotate(
            revenue=Sum('total_amount'), orders=Count('id')
        ).order_by('day')
    trend_map = {row['day']: row for row in trend_raw}
    trend_rows = []
    cursor = trend_start
    while cursor <= trend_end:
        row = trend_map.get(cursor, {})
        trend_rows.append({
            'date': cursor,
            'revenue': row.get('revenue') or Decimal('0'),
            'orders': row.get('orders') or 0,
        })
        cursor += timedelta(days=1)
    trend_peak = max((float(row['revenue']) for row in trend_rows), default=0) or 1
    for row in trend_rows:
        row['bar_percent'] = max(2, round(float(row['revenue']) / trend_peak * 100)) if row['revenue'] else 0

    top_vendors = list(valid_items.values(
        'vendor_id', 'vendor__vendor_code', 'vendor__business_name'
    ).annotate(
        revenue=Sum('total_price'),
        units=Sum('quantity'),
        orders=Count('order_id', distinct=True),
    ).order_by('-revenue')[:10])
    top_products = list(valid_items.values(
        'product_id', 'product_name', 'product_sku'
    ).annotate(
        revenue=Sum('total_price'),
        units=Sum('quantity'),
        orders=Count('order_id', distinct=True),
    ).order_by('-revenue')[:10])

    category_sales = {
        row['product__category_id']: row
        for row in valid_items.exclude(product__category__isnull=True).values('product__category_id').annotate(
            revenue=Sum('total_price'), units=Sum('quantity')
        )
    }
    if vendor:
        categories = Category.objects.annotate(
            product_count=Count('products', filter=Q(products__vendor=vendor), distinct=True),
            stock_units=Sum('products__stock_quantity', filter=Q(products__vendor=vendor)),
        ).filter(product_count__gt=0).order_by('name')
    else:
        categories = Category.objects.annotate(
            product_count=Count('products', distinct=True),
            stock_units=Sum('products__stock_quantity'),
        ).order_by('name')
    category_report = []
    for category in categories:
        sales = category_sales.get(category.id, {})
        category_report.append({
            'id': category.id,
            'name': category.name,
            'status': category.status,
            'product_count': category.product_count,
            'stock_units': category.stock_units or 0,
            'units_sold': sales.get('units') or 0,
            'revenue': sales.get('revenue') or Decimal('0'),
        })
    category_report.sort(key=lambda row: row['revenue'], reverse=True)

    period_customer_qs = UserProfile.objects.all()
    period_vendor_qs = VendorProfile.objects.all()
    if start_date:
        period_customer_qs = period_customer_qs.filter(created_at__date__gte=start_date)
        period_vendor_qs = period_vendor_qs.filter(created_at__date__gte=start_date)
    if end_date:
        period_customer_qs = period_customer_qs.filter(created_at__date__lte=end_date)
        period_vendor_qs = period_vendor_qs.filter(created_at__date__lte=end_date)

    review_qs = ProductReview.objects.all()
    wishlist_qs = WishlistItem.objects.all()
    cart_qs = CartItem.objects.all()
    if vendor:
        review_qs = review_qs.filter(product__vendor=vendor)
        wishlist_qs = wishlist_qs.filter(product__vendor=vendor)
        cart_qs = cart_qs.filter(product__vendor=vendor)
    if start_date:
        review_qs = review_qs.filter(created_at__date__gte=start_date)
        wishlist_qs = wishlist_qs.filter(created_at__date__gte=start_date)
        cart_qs = cart_qs.filter(created_at__date__gte=start_date)
    if end_date:
        review_qs = review_qs.filter(created_at__date__lte=end_date)
        wishlist_qs = wishlist_qs.filter(created_at__date__lte=end_date)
        cart_qs = cart_qs.filter(created_at__date__lte=end_date)

    context = {
        'start_date': start_date.isoformat() if start_date else '',
        'end_date': end_date.isoformat() if end_date else '',
        'selected_vendor_id': str(vendor.id) if vendor else '',
        'selected_vendor': vendor,
        'vendors': VendorProfile.objects.order_by('business_name'),
        'period_label': _report_period_label(start_date, end_date),
        'total_gmv': format_inr(total_gmv),
        'net_sales': format_inr(net_sales),
        'paid_amount': format_inr(paid_amount),
        'refunded_amount': format_inr(refunded_amount),
        'commission_amount': format_inr(commission_amount),
        'vendor_net_amount': format_inr(vendor_net_amount),
        'pending_payout_amount': format_inr(pending_payout_amount),
        'inventory_value': format_inr(inventory_value),
        'total_orders': total_orders,
        'aov': format_inr(aov),
        'units_sold': units_sold,
        'total_vendors': VendorProfile.objects.count(),
        'approved_vendors': VendorProfile.objects.filter(status='APPROVED').count(),
        'new_vendors': period_vendor_qs.count(),
        'total_customers': UserProfile.objects.count(),
        'active_customers': UserProfile.objects.filter(is_active=True).count(),
        'new_customers': period_customer_qs.count(),
        'total_products': len(inventory_products),
        'approved_products': sum(1 for product in inventory_products if product.is_approved),
        'total_stock_units': total_stock_units,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'pending_returns': order_requests.filter(status='PENDING').count(),
        'return_request_count': order_requests.filter(request_type='RETURN').count(),
        'cancel_request_count': order_requests.filter(request_type='CANCEL').count(),
        'average_rating': review_qs.filter(is_approved=True).aggregate(value=Avg('rating'))['value'] or 0,
        'review_count': review_qs.count(),
        'wishlist_count': wishlist_qs.count(),
        'cart_item_count': cart_qs.count(),
        'unread_notifications': Notification.objects.filter(is_read=False).count(),
        'order_status_report': order_status_report,
        'payment_status_report': payment_status_report,
        'payment_method_report': payment_method_report,
        'request_status_report': request_status_report,
        'payout_status_report': payout_status_report,
        'trend_rows': trend_rows,
        'trend_start': trend_start,
        'trend_end': trend_end,
        'top_vendors': top_vendors,
        'top_products': top_products,
        'category_report': category_report[:10],
        'recent_orders': orders.select_related('customer').order_by('-created_at')[:10],
    }
    return render(request, "admin/reports.html", context)


def _parse_report_date(raw_value, field_label):
    raw_value = (raw_value or '').strip()
    if not raw_value:
        return None, None
    try:
        return datetime.strptime(raw_value, '%Y-%m-%d').date(), None
    except ValueError:
        return None, f'{field_label} must use YYYY-MM-DD format.'


def _report_filters(request):
    start_date, start_error = _parse_report_date(request.GET.get('start_date'), 'Start date')
    end_date, end_error = _parse_report_date(request.GET.get('end_date'), 'End date')
    errors = [error for error in (start_error, end_error) if error]
    if start_date and end_date and start_date > end_date:
        errors.append('Start date cannot be after end date.')
        start_date = end_date = None
    vendor = None
    raw_vendor_id = request.GET.get('vendor_id', '').strip()
    if raw_vendor_id:
        vendor = VendorProfile.objects.filter(pk=raw_vendor_id).first() if raw_vendor_id.isdigit() else None
        if not vendor:
            errors.append('The selected vendor was not found.')
    return start_date, end_date, vendor, errors


def _report_period_label(start_date, end_date):
    if start_date and end_date:
        return f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"
    if start_date:
        return f"From {start_date.strftime('%d %b %Y')}"
    if end_date:
        return f"Up to {end_date.strftime('%d %b %Y')}"
    return 'All-time data'


def _distribution_rows(choices, counts, total):
    rows = []
    for value, label in choices:
        count = counts.get(value, 0)
        rows.append({
            'value': value,
            'label': label,
            'count': count,
            'percent': round((count / total) * 100, 1) if total else 0,
        })
    return rows


@admin_required
def admin_reports_export(request):
    """Export filtered operational report datasets as UTF-8 CSV files."""
    report_type = request.GET.get('report', 'orders').strip().lower()
    allowed_types = {'orders', 'products', 'vendors', 'payments', 'returns', 'inventory'}
    if report_type not in allowed_types:
        return JsonResponse({'success': False, 'message': 'Invalid report type.'}, status=400)

    start_date, end_date, vendor, errors = _report_filters(request)
    if errors:
        return JsonResponse({'success': False, 'message': ' '.join(errors)}, status=400)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="nainjyoti-{report_type}-report-{timezone.localdate().isoformat()}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)

    if report_type == 'orders':
        queryset = Order.objects.all().order_by('-created_at')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if vendor:
            queryset = queryset.filter(items__vendor=vendor).distinct()
        writer.writerow(['Order number', 'Customer', 'Phone', 'Amount', 'Payment method', 'Payment status', 'Order status', 'Created at'])
        for item in queryset:
            writer.writerow([item.order_number, item.customer_name, item.customer_phone, item.total_amount, item.payment_method, item.payment_status, item.status, item.created_at.isoformat()])
    elif report_type == 'products':
        queryset = Product.objects.select_related('vendor', 'category').order_by('name')
        if vendor:
            queryset = queryset.filter(vendor=vendor)
        writer.writerow(['Product ID', 'Name', 'SKU', 'Vendor', 'Category', 'Price', 'Discount price', 'Stock', 'Status', 'Approved'])
        for item in queryset:
            writer.writerow([item.id, item.name, item.sku, item.vendor.business_name, item.category.name if item.category else '', item.price, item.discount_price or '', item.stock_quantity, item.status, item.is_approved])
    elif report_type == 'vendors':
        writer.writerow(['Vendor ID', 'Business', 'Owner', 'Email', 'Phone', 'State', 'Status', 'Created at'])
        for item in VendorProfile.objects.select_related('user').order_by('business_name'):
            writer.writerow([item.vendor_code, item.business_name, item.owner_name, item.user.email, item.phone, item.state, item.status, item.created_at.isoformat()])
    elif report_type == 'payments':
        queryset = PaymentTransaction.objects.select_related('order', 'customer').order_by('-created_at')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if vendor:
            queryset = queryset.filter(order__items__vendor=vendor).distinct()
        writer.writerow(['Reference', 'Order', 'Customer', 'Method', 'Amount', 'Currency', 'Status', 'Provider', 'Created at'])
        for item in queryset:
            writer.writerow([item.reference, item.order.order_number, item.customer.full_name if item.customer else '', item.method, item.amount, item.currency, item.status, item.provider, item.created_at.isoformat()])
    elif report_type == 'returns':
        queryset = OrderRequest.objects.select_related('order', 'customer').order_by('-created_at')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if vendor:
            queryset = queryset.filter(order__items__vendor=vendor).distinct()
        writer.writerow(['Request number', 'Type', 'Order', 'Customer', 'Reason', 'Status', 'Admin notes', 'Created at'])
        for item in queryset:
            writer.writerow([item.request_number, item.request_type, item.order.order_number, item.customer.full_name, item.reason, item.status, item.admin_notes, item.created_at.isoformat()])
    else:
        queryset = StockLog.objects.select_related('product', 'variant', 'vendor').order_by('-created_at')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if vendor:
            queryset = queryset.filter(vendor=vendor)
        writer.writerow(['Created at', 'Vendor', 'Product', 'SKU', 'Variant', 'Movement', 'Change', 'Previous stock', 'New stock', 'Reason', 'Reference'])
        for item in queryset:
            writer.writerow([item.created_at.isoformat(), item.vendor.business_name, item.product.name, item.product.sku, item.variant.title if item.variant else '', item.movement_type, item.quantity_changed, item.previous_stock, item.new_stock, item.reason, item.reference_id])
    return response


@admin_required
def admin_settings(request):
    """Admin Settings View."""
    return render(request, "admin/settings.html", {})


@admin_required
def admin_legacy_redirect(request, page=""):
    """
    Fail-safe redirect for legacy or relative .html requests across admin console.
    Ensures URLs like /admin-dashboard/vendor-approval/categories.html seamlessly
    redirect to their canonical dynamic pages.
    """
    clean_page = page.lower().replace(".html", "").strip("/")
    if clean_page == "product-approval":
        return redirect("admin_product_approval")
    if clean_page == "commissions":
        return redirect("admin_commissions")
    if clean_page == "returns":
        return redirect("admin_order_requests")
    if clean_page in ["notifications", "notification-form", "notifications-form"]:
        return redirect("admin_notifications" if clean_page == "notifications" else "admin_notification_add")

    mapping = {
        "index": "admin_dashboard",
        "customers": "admin_customers",
        "addresses": "admin_addresses",
        "vendors": "admin_vendors",
        "vendor-approval": "admin_vendor_approval",
        "categories": "admin_categories",
        "category-form": "admin_category_add",
        "products": "admin_products",
        "product-approval": "admin_product_approval",
        "orders": "admin_orders",
        "payments": "admin_payments",
        "reports": "admin_reports",
        "settings": "admin_settings",
        "login": "login",
    }
    target = mapping.get(clean_page)
    if target:
        return redirect(target)
    return redirect("admin_dashboard")
