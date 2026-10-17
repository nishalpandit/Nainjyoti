import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from .models import UserProfile, OTPRecord, VendorProfile, Category

def _parse_request_data(request):
    """Helper to extract data from JSON body or POST form data."""
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8'))
        except Exception:
            return {}
    return request.POST.dict()

def _get_authenticated_profile(request):
    """
    Authenticate via 'Authorization: Bearer <token>' or 'Authorization: Token <token>'
    or active Django session.
    """
    auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() in ['bearer', 'token']:
            token = parts[1].strip()
            profile = UserProfile.objects.filter(auth_token=token, is_active=True).first()
            if profile:
                return profile

    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        return request.user.customer_profile

    return None


@csrf_exempt
def api_send_otp(request):
    """
    API: Request OTP for Phone Authentication
    Endpoint: POST /api/user/send-otp/
    Body: {"phone": "9876543210", "purpose": "LOGIN"} (or "REGISTER")
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    data = _parse_request_data(request)
    phone = str(data.get("phone", "")).strip().replace(" ", "").replace("-", "")

    if not phone or len(phone) < 10:
        return JsonResponse({
            "success": False,
            "message": "Please provide a valid 10-digit mobile phone number."
        }, status=400)

    # Automatically check if user is already registered or new
    is_registered = UserProfile.objects.filter(phone=phone).exists()
    purpose = "LOGIN" if is_registered else "REGISTER"

    # Generate 6-digit OTP
    otp_record = OTPRecord.generate_for_phone(phone=phone, purpose=purpose)

    # In actual production, SMS Gateway (Twilio/Gupshup/Fast2SMS) would dispatch this.
    print(f"\n=======================================================")
    print(f" [SMS GATEWAY SIMULATION] OTP for {phone}: {otp_record.otp_code} (Action: {purpose})")
    print(f"=======================================================\n")

    message = f"OTP sent for login to {phone}" if is_registered else f"Phone not registered. OTP sent for registration to {phone}"

    return JsonResponse({
        "success": True,
        "message": message,
        "phone": phone,
        "is_registered": is_registered,
        "action": purpose,
        "otp_debug": otp_record.otp_code,  # Provided for easy development & testing
        "expires_in_minutes": 10
    }, status=200)


@csrf_exempt
def api_verify_otp_login(request):
    """
    API: Verify OTP & Sign In User
    Endpoint: POST /api/user/verify-otp-login/
    Body: {"phone": "9876543210", "otp": "123456"}
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    data = _parse_request_data(request)
    phone = str(data.get("phone", "")).strip().replace(" ", "").replace("-", "")
    otp_code = str(data.get("otp", "")).strip()

    if not phone or not otp_code:
        return JsonResponse({
            "success": False,
            "message": "Both 'phone' and 'otp' fields are required."
        }, status=400)

    # Check OTP (support static 123456 in dev or match DB record)
    valid_otp = False
    otp_record = OTPRecord.objects.filter(
        phone=phone,
        otp_code=otp_code,
        is_verified=False,
        expires_at__gt=timezone.now()
    ).first()

    if otp_record:
        otp_record.is_verified = True
        otp_record.save()
        valid_otp = True
    elif otp_code == "123456":  # Standard development fallback
        valid_otp = True

    if not valid_otp:
        return JsonResponse({
            "success": False,
            "message": "Invalid or expired OTP. Please request a new code."
        }, status=400)

    # Check if user profile exists
    profile = UserProfile.objects.filter(phone=phone).first()

    if profile:
        # User is registered -> authenticate and return token
        if not profile.auth_token:
            profile.generate_new_token()

        if hasattr(request, 'session'):
            login(request, profile.user)

        return JsonResponse({
            "success": True,
            "message": "Login successful",
            "is_registered": True,
            "token": profile.auth_token,
            "user": profile.to_dict()
        }, status=200)
    else:
        # Phone verified but user is not registered yet
        return JsonResponse({
            "success": True,
            "message": "Phone number verified. Please complete user registration.",
            "is_registered": False,
            "phone": phone,
            "otp_verified": True
        }, status=200)


@csrf_exempt
def api_user_register(request):
    """
    API: Register New User with Full Profile Details
    Endpoint: POST /api/user/register/
    Accepts: multipart/form-data or application/json
    Fields:
      - first_name (required)
      - last_name (required)
      - phone (required)
      - email (optional)
      - dob (optional, YYYY-MM-DD)
      - gender (Male/Female/Other/Prefer not to say)
      - profile_photo (file, optional)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    data = _parse_request_data(request)

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    phone = str(data.get("phone", "")).strip().replace(" ", "").replace("-", "")
    email = data.get("email", "").strip().lower() or None
    dob_raw = data.get("dob", "").strip()
    gender = data.get("gender", "Prefer not to say").strip()

    # Profile photo can be in request.FILES
    profile_photo = request.FILES.get("profile_photo", None)

    # Validations
    if not first_name or not last_name:
        return JsonResponse({
            "success": False,
            "message": "Both First Name and Last Name are required."
        }, status=400)

    if not phone or len(phone) < 10:
        return JsonResponse({
            "success": False,
            "message": "A valid 10-digit mobile phone number is required."
        }, status=400)

    # Check if phone already registered
    if UserProfile.objects.filter(phone=phone).exists():
        return JsonResponse({
            "success": False,
            "message": f"An account with phone number {phone} is already registered. Please sign in with OTP."
        }, status=400)

    # Parse DOB if provided
    dob_parsed = None
    if dob_raw:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                dob_parsed = datetime.strptime(dob_raw, fmt).date()
                break
            except ValueError:
                continue

    # Ensure unique auth username
    base_username = f"usr_{phone}"
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{counter}"
        counter += 1

    # Create Django User
    user = User.objects.create_user(
        username=username,
        email=email or "",
        first_name=first_name,
        last_name=last_name
    )
    user.set_unusable_password()
    user.save()

    # Create Customer UserProfile
    profile = UserProfile.objects.create(
        user=user,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        email=email,
        dob=dob_parsed,
        gender=gender,
        profile_photo=profile_photo
    )

    if hasattr(request, 'session'):
        login(request, user)

    return JsonResponse({
        "success": True,
        "message": "User registered successfully",
        "token": profile.auth_token,
        "user": profile.to_dict()
    }, status=201)


@csrf_exempt
def api_user_profile(request):
    """
    API: Get or Update Authenticated User Profile
    Endpoint: GET, PUT/POST /api/user/profile/
    Header: Authorization: Bearer <token>
    """
    profile = _get_authenticated_profile(request)
    if not profile:
        return JsonResponse({
            "success": False,
            "message": "Authentication required. Pass valid Bearer token in 'Authorization' header."
        }, status=401)

    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "user": profile.to_dict()
        }, status=200)

    elif request.method in ["POST", "PUT"]:
        data = _parse_request_data(request)

        if "first_name" in data and data["first_name"].strip():
            profile.first_name = data["first_name"].strip()
            profile.user.first_name = profile.first_name

        if "last_name" in data and data["last_name"].strip():
            profile.last_name = data["last_name"].strip()
            profile.user.last_name = profile.last_name

        if "email" in data:
            profile.email = data["email"].strip().lower() or None
            profile.user.email = profile.email or ""

        if "gender" in data:
            profile.gender = data["gender"]

        if "dob" in data and data["dob"]:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    profile.dob = datetime.strptime(data["dob"].strip(), fmt).date()
                    break
                except ValueError:
                    continue

        if "profile_photo" in request.FILES:
            profile.profile_photo = request.FILES["profile_photo"]

        profile.user.save()
        profile.save()

        return JsonResponse({
            "success": True,
            "message": "Profile updated successfully",
            "user": profile.to_dict()
        }, status=200)

    return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)


@csrf_exempt
def api_user_logout(request):
    """
    API: Logout user & rotate/invalidate token
    Endpoint: POST /api/user/logout/
    """
    profile = _get_authenticated_profile(request)
    if profile:
        profile.generate_new_token()  # Invalidate previous token

    if hasattr(request, 'session'):
        logout(request)

    return JsonResponse({
        "success": True,
        "message": "User successfully logged out"
    }, status=200)


# =============================================================================
# VENDOR REST APIS (Registration, Login, Profile & Status Tracking)
# =============================================================================

def _get_authenticated_vendor(request):
    """
    Authenticate vendor via 'Authorization: Bearer <token>'
    or active Django session with vendor_profile.
    """
    auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() in ['bearer', 'token']:
            token = parts[1].strip()
            vendor = VendorProfile.objects.filter(auth_token=token).first()
            if vendor:
                return vendor

    if request.user.is_authenticated and hasattr(request.user, 'vendor_profile'):
        return request.user.vendor_profile

    return None


@csrf_exempt
def api_vendor_register(request):
    """
    API: Register a new Vendor / Merchant Store
    Endpoint: POST /api/vendor/register/
    Accepts: JSON or form-data (supports document file uploads)
    Fields:
      - business_name (required)
      - owner_name (required)
      - email (required)
      - phone (required)
      - password (required, min 6 chars)
      - category (optional, default: 'General Merchandise')
      - business_type (optional, default: 'Retailer')
      - gst_number (optional)
      - pan_number (optional)
      - address, city, state, pincode (optional)
      - bank_name, account_number, ifsc_code (optional)
      - gst_document, pan_document, id_proof (optional files)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    data = _parse_request_data(request)

    business_name = data.get("business_name", "").strip()
    owner_name = data.get("owner_name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = str(data.get("phone", "")).strip().replace(" ", "").replace("-", "")
    password = data.get("password", "")

    category = data.get("category", "General Merchandise").strip() or "General Merchandise"
    business_type = data.get("business_type", "Retailer").strip() or "Retailer"

    gst_number = data.get("gst_number", "").strip().upper()
    pan_number = data.get("pan_number", "").strip().upper()

    address = data.get("address", "").strip()
    city = data.get("city", "").strip()
    state = data.get("state", "").strip()
    pincode = str(data.get("pincode", "")).strip()

    bank_name = data.get("bank_name", "").strip()
    account_number = str(data.get("account_number", "")).strip()
    ifsc_code = data.get("ifsc_code", "").strip().upper()

    # Validations
    if not business_name or not owner_name:
        return JsonResponse({
            "success": False,
            "message": "Both 'business_name' and 'owner_name' are required fields."
        }, status=400)

    if not email or "@" not in email:
        return JsonResponse({
            "success": False,
            "message": "A valid 'email' address is required for vendor account creation."
        }, status=400)

    if not phone or len(phone) < 10:
        return JsonResponse({
            "success": False,
            "message": "A valid 10-digit 'phone' number is required."
        }, status=400)

    if not password or len(password) < 6:
        return JsonResponse({
            "success": False,
            "message": "Password must be at least 6 characters in length."
        }, status=400)

    # Check if user with this email already exists
    if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
        return JsonResponse({
            "success": False,
            "message": f"An account with email '{email}' already exists. Please log in."
        }, status=400)

    # Prevent duplicate phone number registration
    if VendorProfile.objects.filter(phone=phone).exists():
        return JsonResponse({
            "success": False,
            "message": f"A seller store is already registered with mobile number '{phone}'. Please use a unique phone number."
        }, status=400)

    # Prevent duplicate GSTIN registration
    if gst_number and VendorProfile.objects.filter(gst_number__iexact=gst_number).exists():
        return JsonResponse({
            "success": False,
            "message": f"A seller store is already registered with GSTIN '{gst_number}'. Duplicate GST registration is not permitted."
        }, status=400)

    # Prevent duplicate PAN registration
    if pan_number and VendorProfile.objects.filter(pan_number__iexact=pan_number).exists():
        return JsonResponse({
            "success": False,
            "message": f"A seller store is already registered with PAN '{pan_number}'. Duplicate PAN registration is not permitted."
        }, status=400)

    # Prevent duplicate Store / Business Name
    if VendorProfile.objects.filter(business_name__iexact=business_name).exists():
        return JsonResponse({
            "success": False,
            "message": f"A store named '{business_name}' is already registered. Please choose a unique business name."
        }, status=400)

    # Create Django User
    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=owner_name,
        is_staff=False,
        is_superuser=False
    )

    # File attachments if present
    gst_document = request.FILES.get("gst_document", None)
    pan_document = request.FILES.get("pan_document", None)
    id_proof = request.FILES.get("id_proof", None)

    # Create VendorProfile with status PENDING
    vendor = VendorProfile.objects.create(
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
        gst_document=gst_document,
        pan_document=pan_document,
        id_proof=id_proof,
        status="PENDING"
    )

    return JsonResponse({
        "success": True,
        "message": "Vendor registration submitted successfully! Your application is under compliance review.",
        "vendor_code": vendor.vendor_code,
        "status": vendor.status,
        "token": vendor.auth_token,
        "vendor": vendor.to_dict()
    }, status=201)


@csrf_exempt
def api_vendor_login(request):
    """
    API: Vendor Store Sign In
    Endpoint: POST /api/vendor/login/
    Fields:
      - username or email (required, can be email or vendor_code)
      - password (required)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    data = _parse_request_data(request)
    identifier = str(data.get("username", "") or data.get("email", "")).strip()
    password = str(data.get("password", "")).strip()

    if not identifier or not password:
        return JsonResponse({
            "success": False,
            "message": "Both identifier ('username'/'email') and 'password' are required."
        }, status=400)

    # Lookup user by username, email, or vendor_code
    user_obj = User.objects.filter(
        Q(username__iexact=identifier) |
        Q(email__iexact=identifier) |
        Q(vendor_profile__vendor_code__iexact=identifier)
    ).first()

    user = None
    if user_obj:
        user = authenticate(request, username=user_obj.username, password=password)

    if user is None:
        return JsonResponse({
            "success": False,
            "message": "Invalid seller credentials. Please verify your email/username and password."
        }, status=401)

    # Check for Admin role
    if user.is_staff or user.is_superuser:
        if hasattr(request, 'session'):
            login(request, user)
        return JsonResponse({
            "success": True,
            "message": f"Welcome back, Administrator {user.first_name or user.username}!",
            "role": "ADMIN",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser
            }
        }, status=200)

    # Check for Vendor profile
    if hasattr(user, 'vendor_profile'):
        vendor = user.vendor_profile

        if vendor.status == "APPROVED":
            if not vendor.auth_token:
                vendor.generate_new_token()
            if hasattr(request, 'session'):
                login(request, user)
            return JsonResponse({
                "success": True,
                "message": f"Login successful. Welcome back to your seller console, {vendor.business_name}!",
                "status": "APPROVED",
                "role": "VENDOR",
                "token": vendor.auth_token,
                "vendor": vendor.to_dict()
            }, status=200)

        elif vendor.status == "PENDING":
            return JsonResponse({
                "success": False,
                "status": "PENDING",
                "vendor_code": vendor.vendor_code,
                "message": f"Application Under Review: Your store '{vendor.business_name}' ({vendor.vendor_code}) is awaiting Admin review. You will be able to access the dashboard once approved."
            }, status=403)

        elif vendor.status == "REJECTED":
            return JsonResponse({
                "success": False,
                "status": "REJECTED",
                "vendor_code": vendor.vendor_code,
                "rejection_reason": vendor.rejection_reason or "Submitted documents could not be validated.",
                "message": f"Application Declined: Store registration was not approved. Reason: {vendor.rejection_reason or 'Document verification failed.'}"
            }, status=403)

    return JsonResponse({
        "success": False,
        "message": "No active vendor account found for these credentials."
    }, status=404)


@csrf_exempt
def api_vendor_profile(request):
    """
    API: Get or Update Authenticated Vendor Store Profile
    Endpoint: GET, PUT/POST /api/vendor/profile/
    Header: Authorization: Bearer <token>
    """
    vendor = _get_authenticated_vendor(request)
    if not vendor:
        return JsonResponse({
            "success": False,
            "message": "Authentication required. Pass valid Vendor Bearer token in 'Authorization' header."
        }, status=401)

    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "vendor": vendor.to_dict()
        }, status=200)

    elif request.method in ["POST", "PUT"]:
        data = _parse_request_data(request)

        # Allow updating editable profile fields
        editable_fields = [
            "business_name", "owner_name", "phone", "category", "business_type",
            "address", "city", "state", "pincode", "bank_name", "account_number",
            "ifsc_code", "gst_number", "pan_number", "store_description", "support_email"
        ]

        for field in editable_fields:
            if field in data and str(data[field]).strip() != "":
                setattr(vendor, field, str(data[field]).strip())

        if "owner_name" in data and data["owner_name"].strip():
            vendor.user.first_name = data["owner_name"].strip()
            vendor.user.save()

        # Handle branding & document file updates
        if "store_logo" in request.FILES:
            vendor.store_logo = request.FILES["store_logo"]
        if "store_banner" in request.FILES:
            vendor.store_banner = request.FILES["store_banner"]
        if "gst_document" in request.FILES:
            vendor.gst_document = request.FILES["gst_document"]
        if "pan_document" in request.FILES:
            vendor.pan_document = request.FILES["pan_document"]
        if "id_proof" in request.FILES:
            vendor.id_proof = request.FILES["id_proof"]

        vendor.save()

        return JsonResponse({
            "success": True,
            "message": "Store profile updated successfully",
            "vendor": vendor.to_dict()
        }, status=200)

    return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)


@csrf_exempt
def api_vendor_change_password(request):
    """
    API: Change Vendor Account Password
    Endpoint: POST /api/vendor/profile/change-password/
    Header: Authorization: Bearer <token>
    Fields:
      - current_password (required)
      - new_password (required, min 6 chars)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    vendor = _get_authenticated_vendor(request)
    if not vendor:
        return JsonResponse({
            "success": False,
            "message": "Authentication required. Pass valid Vendor Bearer token in 'Authorization' header."
        }, status=401)

    data = _parse_request_data(request)
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return JsonResponse({
            "success": False,
            "message": "Both 'current_password' and 'new_password' are required."
        }, status=400)

    if not vendor.user.check_password(current_password):
        return JsonResponse({
            "success": False,
            "message": "Current password is incorrect. Please re-enter."
        }, status=400)

    if len(new_password) < 6:
        return JsonResponse({
            "success": False,
            "message": "New password must be at least 6 characters in length."
        }, status=400)

    vendor.user.set_password(new_password)
    vendor.user.save()
    vendor.generate_new_token()

    return JsonResponse({
        "success": True,
        "message": "Password updated successfully. New token generated.",
        "token": vendor.auth_token
    }, status=200)


@csrf_exempt
def api_vendor_status_lookup(request):
    """
    API: Track Vendor Application Status by Reference Code or Email (Public)
    Endpoint: GET, POST /api/vendor/status/
    Params / Body: code=VEND-XXXXX or email=seller@domain.com
    """
    if request.method == "GET":
        query = request.GET.get("code", "") or request.GET.get("query", "") or request.GET.get("email", "")
    else:
        data = _parse_request_data(request)
        query = data.get("code", "") or data.get("query", "") or data.get("email", "")

    query = str(query).strip()
    if not query:
        return JsonResponse({
            "success": False,
            "message": "Please provide a 'code' (e.g. VEND-12345) or 'email' to track application status."
        }, status=400)

    vendor = VendorProfile.objects.filter(
        Q(vendor_code__iexact=query) | Q(user__email__iexact=query) | Q(phone__iexact=query)
    ).first()

    if not vendor:
        return JsonResponse({
            "success": False,
            "message": f"No vendor application found matching reference '{query}'."
        }, status=404)

    return JsonResponse({
        "success": True,
        "vendor_code": vendor.vendor_code,
        "business_name": vendor.business_name,
        "owner_name": vendor.owner_name,
        "status": vendor.status,
        "status_display": vendor.get_status_display(),
        "rejection_reason": vendor.rejection_reason if vendor.status == "REJECTED" else None,
        "submitted_at": vendor.created_at.isoformat(),
        "updated_at": vendor.updated_at.isoformat()
    }, status=200)


@csrf_exempt
def api_vendor_logout(request):
    """
    API: Logout vendor & rotate token
    Endpoint: POST /api/vendor/logout/
    Header: Authorization: Bearer <token>
    """
    vendor = _get_authenticated_vendor(request)
    if vendor:
        vendor.generate_new_token()  # Invalidate token

    if hasattr(request, 'session'):
        logout(request)

    return JsonResponse({
        "success": True,
        "message": "Vendor successfully logged out"
    }, status=200)


# =============================================================================
# CATEGORY MANAGEMENT REST APIS
# =============================================================================

def _handle_category_delete(request, category):
    cat_name = category.name
    cat_id = category.id

    soft = request.GET.get("soft", "").strip().lower() in ["true", "1"]
    if soft:
        category.is_active = False
        category.save()
        return JsonResponse({
            "success": True,
            "message": f"Category '{cat_name}' marked as inactive (soft deleted).",
            "category_id": cat_id,
            "is_active": False
        }, status=200)

    subcategories_count = category.subcategories.count()
    category.delete()

    msg = f"Category '{cat_name}' (ID: {cat_id}) deleted successfully."
    if subcategories_count > 0:
        msg += f" {subcategories_count} associated subcategories were also removed."

    return JsonResponse({
        "success": True,
        "message": msg,
        "category_id": cat_id
    }, status=200)


@csrf_exempt
def api_category_list_create(request):
    """
    API: List categories or create a new category / subcategory.
    Endpoints:
      - GET  /api/categories/
      - POST /api/categories/
    Query Filters (GET):
      - parent: 'null', 'root', or 'top' for top-level only
      - parent_id: integer ID of parent category
      - search: string to search in name or description
      - all: 'true' to include inactive categories (default: only active)
      - tree: 'true' to return hierarchical tree of categories
    Body Parameters (POST):
      - name: string (required, unique)
      - slug: string (optional, auto-generated from name if omitted)
      - description: string (optional)
      - parent_id: integer (optional, for subcategory creation)
      - commission_rate: decimal (optional, default: 5.00)
      - icon: string (optional, default: 'fa-layer-group')
      - display_order: integer (optional, default: 0)
      - is_active: boolean (optional, default: True)
      - image: file (optional)
    """
    if request.method == "GET":
        qs = Category.objects.all()

        show_all = request.GET.get("all", "").strip().lower() in ["true", "1"]
        if not show_all:
            qs = qs.filter(is_active=True)

        parent_param = request.GET.get("parent", "").strip().lower()
        if parent_param in ["null", "none", "root", "top"]:
            qs = qs.filter(parent__isnull=True)

        parent_id = request.GET.get("parent_id")
        if parent_id and parent_id.isdigit():
            qs = qs.filter(parent_id=int(parent_id))

        search = request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        tree_mode = request.GET.get("tree", "").strip().lower() in ["true", "1"]
        if tree_mode:
            qs = qs.filter(parent__isnull=True)
            categories = [cat.to_dict(include_subcategories=True) for cat in qs]
        else:
            categories = [cat.to_dict(include_subcategories=False) for cat in qs]

        return JsonResponse({
            "success": True,
            "count": len(categories),
            "categories": categories
        }, status=200)

    elif request.method == "POST":
        data = _parse_request_data(request)

        name = data.get("name", "").strip()
        if not name:
            return JsonResponse({
                "success": False,
                "message": "Category 'name' is required."
            }, status=400)

        if Category.objects.filter(name__iexact=name).exists():
            return JsonResponse({
                "success": False,
                "message": f"Category with name '{name}' already exists."
            }, status=400)

        slug = data.get("slug", "").strip()
        if slug:
            slug = slugify(slug)
            if Category.objects.filter(slug=slug).exists():
                return JsonResponse({
                    "success": False,
                    "message": f"Category with slug '{slug}' already exists."
                }, status=400)

        description = data.get("description", "").strip()

        parent = None
        parent_id = data.get("parent_id")
        if parent_id:
            try:
                parent = Category.objects.get(id=int(parent_id))
            except (Category.DoesNotExist, ValueError):
                return JsonResponse({
                    "success": False,
                    "message": f"Parent category with ID '{parent_id}' does not exist."
                }, status=400)

        try:
            commission_rate = float(data.get("commission_rate", 5.00))
        except (ValueError, TypeError):
            commission_rate = 5.00

        try:
            display_order = int(data.get("display_order", 0))
        except (ValueError, TypeError):
            display_order = 0

        icon = data.get("icon", "fa-layer-group").strip() or "fa-layer-group"

        is_active = data.get("is_active", True)
        if isinstance(is_active, str):
            is_active = is_active.lower() not in ["false", "0", "no"]

        category = Category(
            name=name,
            slug=slug,
            description=description,
            parent=parent,
            commission_rate=commission_rate,
            icon=icon,
            display_order=display_order,
            is_active=is_active
        )

        if "image" in request.FILES:
            category.image = request.FILES["image"]

        category.save()

        return JsonResponse({
            "success": True,
            "message": "Category created successfully",
            "category": category.to_dict(include_subcategories=True)
        }, status=201)

    return JsonResponse({"success": False, "message": "Method not allowed. Use GET or POST."}, status=405)


@csrf_exempt
def api_category_detail_update_delete(request, category_id=None, slug=None):
    """
    API: Retrieve, Update, or Delete a single category.
    Endpoints:
      - GET    /api/categories/<id>/  or  /api/categories/slug/<slug>/
      - PUT    /api/categories/<id>/
      - POST   /api/categories/<id>/update/  or  /api/categories/<id>/
      - DELETE /api/categories/<id>/
      - POST   /api/categories/<id>/delete/
    """
    category = None
    if category_id:
        category = Category.objects.filter(id=category_id).first()
    elif slug:
        category = Category.objects.filter(slug=slug).first()

    if not category:
        return JsonResponse({
            "success": False,
            "message": "Category not found."
        }, status=404)

    # 1. GET Category Detail
    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "category": category.to_dict(include_subcategories=True)
        }, status=200)

    # 2. UPDATE Category (PUT or POST)
    elif request.method in ["PUT", "POST"]:
        # Check if routed via /delete
        if request.path.rstrip('/').endswith('/delete'):
            return _handle_category_delete(request, category)

        data = _parse_request_data(request)

        # Update name
        if "name" in data and data["name"].strip():
            new_name = data["name"].strip()
            if Category.objects.filter(name__iexact=new_name).exclude(pk=category.pk).exists():
                return JsonResponse({
                    "success": False,
                    "message": f"Another category with name '{new_name}' already exists."
                }, status=400)
            category.name = new_name

        # Update slug
        if "slug" in data and data["slug"].strip():
            new_slug = slugify(data["slug"].strip())
            if Category.objects.filter(slug=new_slug).exclude(pk=category.pk).exists():
                return JsonResponse({
                    "success": False,
                    "message": f"Another category with slug '{new_slug}' already exists."
                }, status=400)
            category.slug = new_slug

        # Update description
        if "description" in data:
            category.description = data["description"].strip()

        # Update parent
        if "parent_id" in data:
            pid = data["parent_id"]
            if pid is None or pid == "" or pid == "null" or pid == 0 or pid == "0":
                category.parent = None
            else:
                try:
                    pid = int(pid)
                    if pid == category.id:
                        return JsonResponse({
                            "success": False,
                            "message": "A category cannot be set as its own parent."
                        }, status=400)
                    parent = Category.objects.get(id=pid)
                    category.parent = parent
                except (Category.DoesNotExist, ValueError):
                    return JsonResponse({
                        "success": False,
                        "message": f"Parent category with ID '{pid}' does not exist."
                    }, status=400)

        # Update commission_rate
        if "commission_rate" in data:
            try:
                category.commission_rate = float(data["commission_rate"])
            except (ValueError, TypeError):
                pass

        # Update display_order
        if "display_order" in data:
            try:
                category.display_order = int(data["display_order"])
            except (ValueError, TypeError):
                pass

        # Update icon
        if "icon" in data and data["icon"].strip():
            category.icon = data["icon"].strip()

        # Update is_active
        if "is_active" in data:
            is_active = data["is_active"]
            if isinstance(is_active, str):
                category.is_active = is_active.lower() not in ["false", "0", "no"]
            else:
                category.is_active = bool(is_active)

        # Update image
        if "image" in request.FILES:
            category.image = request.FILES["image"]

        category.save()

        return JsonResponse({
            "success": True,
            "message": "Category updated successfully",
            "category": category.to_dict(include_subcategories=True)
        }, status=200)

    # 3. DELETE Category
    elif request.method == "DELETE":
        return _handle_category_delete(request, category)

    return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)


@csrf_exempt
def api_category_tree(request):
    """
    API: Returns complete Category Hierarchy Tree (Top-level -> Subcategories)
    Endpoint: GET /api/categories/tree/
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    root_categories = Category.objects.filter(parent__isnull=True, is_active=True).order_by('display_order', 'name')
    tree = [cat.to_dict(include_subcategories=True) for cat in root_categories]

    return JsonResponse({
        "success": True,
        "count": len(tree),
        "tree": tree
    }, status=200)

