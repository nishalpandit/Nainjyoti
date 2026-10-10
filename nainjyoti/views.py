from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from .models import VendorProfile

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


def admin_dashboard(request):
    """Admin Overview Dashboard with dynamic statistics."""
    pending_count = VendorProfile.objects.filter(status="PENDING").count()
    approved_count = VendorProfile.objects.filter(status="APPROVED").count()
    recent_vendors = VendorProfile.objects.all()[:5]

    return render(request, "admin/index.html", {
        "pending_vendors_count": pending_count,
        "approved_vendors_count": approved_count,
        "recent_vendors": recent_vendors
    })


def admin_vendor_approval(request):
    """
    Admin portal to review pending vendor applications, inspect documents,
    and Approve or Reject stores.
    """
    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id")
        action = request.POST.get("action")
        vendor = get_object_or_404(VendorProfile, id=vendor_id)

        if action == "approve":
            vendor.status = "APPROVED"
            vendor.save()
            messages.success(request, f"Successfully APPROVED store '{vendor.business_name}' ({vendor.vendor_code})! The vendor can now log in.")
        elif action == "reject":
            reason = request.POST.get("reason", "Submitted business verification documents could not be validated.")
            vendor.status = "REJECTED"
            vendor.rejection_reason = reason
            vendor.save()
            messages.warning(request, f"Rejected store application '{vendor.business_name}'.")

        return redirect("admin_vendor_approval")

    filter_status = request.GET.get("status", "ALL")
    search_query = request.GET.get("q", "").strip()

    vendors = VendorProfile.objects.all()
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
            Q(state__icontains=search_query)
        )

    pending_count = VendorProfile.objects.filter(status="PENDING").count()
    approved_count = VendorProfile.objects.filter(status="APPROVED").count()

    return render(request, "admin/vendor-approval.html", {
        "vendors": vendors,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "current_status": filter_status,
        "search_query": search_query
    })


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
