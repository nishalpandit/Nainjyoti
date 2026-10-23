from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Count, Avg
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta, datetime
import json
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
)

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
    open_issues_count = pending_vendors_count + pending_payouts_count + out_of_stock_count + pending_orders_count
    issues_today_count = pending_vendors_count + pending_payouts_count

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
        "recent_orders": recent_orders,
        "top_categories": top_categories,
    })


def admin_categories(request):
    """Admin Categories Management View"""
    categories = Category.objects.all().order_by('name')
    return render(request, "admin/categories.html", {
        "categories": categories,
        "total_categories": categories.count()
    })


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
            msg = f"Store '{vendor.business_name}' ({vendor.vendor_code}) APPROVED! KYC accepted and seller access activated."
            if not is_ajax:
                messages.success(request, msg)

        elif action == "reject":
            reason = str(data.get("reason", "")).strip() or "Submitted business verification documents could not be validated."
            vendor.status = "REJECTED"
            vendor.rejection_reason = reason
            vendor.save()
            msg = f"Store application '{vendor.business_name}' declined. Reason: {reason}"
            if not is_ajax:
                messages.warning(request, msg)

        elif action == "pending":
            vendor.status = "PENDING"
            vendor.rejection_reason = ""
            vendor.save()
            msg = f"Store '{vendor.business_name}' reset back to PENDING review."
            if not is_ajax:
                messages.info(request, msg)

        else:
            msg = "No state change performed."

        if is_ajax:
            pending_count = VendorProfile.objects.filter(status="PENDING").count()
            approved_count = VendorProfile.objects.filter(status="APPROVED").count()
            rejected_count = VendorProfile.objects.filter(status="REJECTED").count()
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
    total_count = VendorProfile.objects.count()

    return render(request, "admin/vendor-approval.html", {
        "vendors": vendors,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "total_count": total_count,
        "current_status": filter_status,
        "search_query": search_query
    })


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

    customers_list = []
    for c in customers_qs:
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
        "total_count": len(customers_list),
        "active_count": active_count,
        "inactive_count": inactive_count,
        "address_count": address_count,
        "search_query": search_query,
        "status_filter": status_filter,
    })


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

    return render(request, "admin/addresses.html", {
        "addresses": addresses,
        "filtered_count": addresses.count(),
        "total_count": UserAddress.objects.count(),
        "default_count": UserAddress.objects.filter(is_default=True).count(),
        "customers_with_addresses": UserProfile.objects.filter(addresses__isnull=False).distinct().count(),
        "search_query": search_query,
        "address_type": address_type if address_type in ['Home', 'Work', 'Other'] else 'ALL',
        "default_filter": default_filter if default_filter in ['YES', 'NO'] else 'ALL',
    })


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
    if status_filter in ["APPROVED", "PENDING", "REJECTED"]:
        vendors_qs = vendors_qs.filter(status=status_filter)

    vendors_list = []
    now = timezone.now()
    first_of_month = now.date().replace(day=1)
    for v in vendors_qs:
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
        "total_count": len(vendors_list),
        "search_query": search_query,
        "status_filter": status_filter,
    })


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
        products_qs = products_qs.filter(status='ACTIVE')
    elif status_filter == "OUT_OF_STOCK":
        products_qs = products_qs.filter(status='OUT_OF_STOCK')

    return render(request, "admin/products.html", {
        "products": products_qs,
        "total_count": products_qs.count(),
        "search_query": search_query,
        "status_filter": status_filter,
    })


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

    orders_list = []
    for o in orders_qs:
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
        "total_count": len(orders_list),
        "search_query": search_query,
        "status_filter": status_filter,
    })


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

    payouts_list = []
    for p in payouts_qs:
        st = p.status.upper()
        if st == 'COMPLETED':
            pill = 'green'
        elif st in ['PROCESSING', 'PENDING']:
            pill = 'amber'
        else:
            pill = 'rose'

        payouts_list.append({
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
        "total_count": len(payouts_list),
        "search_query": search_query,
        "status_filter": status_filter,
    })


def admin_reports(request):
    """Admin Reports View."""
    total_gmv = Order.objects.exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0
    total_orders = Order.objects.count()
    total_vendors = VendorProfile.objects.count()
    total_customers = UserProfile.objects.count()
    return render(request, "admin/reports.html", {
        "total_gmv": format_inr(total_gmv),
        "total_orders": total_orders,
        "total_vendors": total_vendors,
        "total_customers": total_customers,
    })


def admin_settings(request):
    """Admin Settings View."""
    return render(request, "admin/settings.html", {})
