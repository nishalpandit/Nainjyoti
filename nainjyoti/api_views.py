import json
import base64
import random
import secrets
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.base import ContentFile
from .models import UserProfile, OTPRecord, VendorProfile, Category, Product, StockLog

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


def _require_vendor_auth(request):
    """
    Strictly enforce Vendor Bearer token authentication.
    Returns (vendor, None) on success, or (None, JsonResponse) on failure (401 / 403).
    """
    vendor = _get_authenticated_vendor(request)
    if not vendor:
        return None, JsonResponse({
            "success": False,
            "message": "Authentication required. Please provide a valid Vendor Bearer token in the 'Authorization' header."
        }, status=401)

    if vendor.status != "APPROVED":
        return None, JsonResponse({
            "success": False,
            "message": f"Store status '{vendor.status}' is not authorized. Only APPROVED vendors can access this endpoint."
        }, status=403)

    return vendor, None


def _check_vendor_ownership(vendor, product, action_name="manage"):
    """
    Strictly verify multi-tenant item ownership.
    Returns None if permitted, or JsonResponse 403 if vendor does not own this product.
    """
    if product.vendor_id != vendor.id:
        return JsonResponse({
            "success": False,
            "message": f"Access denied. You do not have permission to {action_name} this product."
        }, status=403)
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
# CATEGORY MANAGEMENT MASTER APIS (Name and Status Only)
# =============================================================================

def _normalize_category_status(status_val):
    """Helper to normalize status string or boolean to 'ACTIVE' or 'INACTIVE'."""
    if isinstance(status_val, bool):
        return 'ACTIVE' if status_val else 'INACTIVE'
    s = str(status_val or 'ACTIVE').strip().upper()
    if s in ['ACTIVE', 'ENABLED', 'ENABLE', 'TRUE', '1', 'VISIBLE']:
        return 'ACTIVE'
    elif s in ['INACTIVE', 'DISABLED', 'DISABLE', 'FALSE', '0', 'HIDDEN']:
        return 'INACTIVE'
    return 'ACTIVE'


@csrf_exempt
def api_category_list(request):
    """
    API: List Master Categories
    Method: GET
    Query Filters:
      - status: 'ACTIVE' or 'INACTIVE' (optional)
      - search: string to search in category name (optional)
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    qs = Category.objects.all()

    status_param = request.GET.get("status", "").strip().upper()
    if status_param in ["ACTIVE", "INACTIVE"]:
        qs = qs.filter(status=status_param)

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(name__icontains=search)

    categories = [cat.to_dict() for cat in qs]

    return JsonResponse({
        "success": True,
        "count": len(categories),
        "categories": categories
    }, status=200)


@csrf_exempt
def api_category_create(request):
    """
    API: Create Master Category
    Method: POST
    Params:
      - name: string (required, unique)
      - status: string 'ACTIVE' or 'INACTIVE' (optional, default: 'ACTIVE')
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

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

    status_val = _normalize_category_status(data.get("status", "ACTIVE"))

    category = Category.objects.create(
        name=name,
        status=status_val
    )

    return JsonResponse({
        "success": True,
        "message": "Category created successfully",
        "category": category.to_dict()
    }, status=201)


@csrf_exempt
def api_category_detail(request, category_id=None, slug=None):
    """
    API: Retrieve Master Category Details
    Method: GET
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    category = Category.objects.filter(id=category_id).first()
    if not category:
        return JsonResponse({
            "success": False,
            "message": f"Category with ID '{category_id}' not found."
        }, status=404)

    return JsonResponse({
        "success": True,
        "category": category.to_dict()
    }, status=200)


@csrf_exempt
def api_category_update(request, category_id):
    """
    API: Update Master Category (name and/or status)
    Method: POST or PUT
    Params:
      - name: string (optional)
      - status: string 'ACTIVE' or 'INACTIVE' (optional)
    """
    if request.method not in ["POST", "PUT"]:
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST or PUT."}, status=405)

    category = Category.objects.filter(id=category_id).first()
    if not category:
        return JsonResponse({
            "success": False,
            "message": f"Category with ID '{category_id}' not found."
        }, status=404)

    data = _parse_request_data(request)

    if "name" in data and data["name"].strip():
        new_name = data["name"].strip()
        if Category.objects.filter(name__iexact=new_name).exclude(pk=category.pk).exists():
            return JsonResponse({
                "success": False,
                "message": f"Another category with name '{new_name}' already exists."
            }, status=400)
        category.name = new_name

    if "status" in data:
        category.status = _normalize_category_status(data["status"])

    category.save()

    return JsonResponse({
        "success": True,
        "message": "Category updated successfully",
        "category": category.to_dict()
    }, status=200)


@csrf_exempt
def api_category_delete(request, category_id):
    """
    API: Delete Master Category
    Method: POST or DELETE
    """
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST or DELETE."}, status=405)

    category = Category.objects.filter(id=category_id).first()
    if not category:
        return JsonResponse({
            "success": False,
            "message": f"Category with ID '{category_id}' not found."
        }, status=404)

    cat_name = category.name
    cat_id = category.id
    category.delete()

    return JsonResponse({
        "success": True,
        "message": f"Category '{cat_name}' (ID: {cat_id}) deleted successfully.",
        "category_id": cat_id
    }, status=200)


@csrf_exempt
def api_category_tree(request):
    """API alias for category hierarchy / list"""
    return api_category_list(request)


# Backward compatibility wrappers
@csrf_exempt
def api_category_list_create(request):
    if request.method == "GET":
        return api_category_list(request)
    elif request.method == "POST":
        return api_category_create(request)
    return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)


@csrf_exempt
def api_category_detail_update_delete(request, category_id=None, slug=None):
    if request.method == "GET":
        return api_category_detail(request, category_id=category_id)
    elif request.method in ["PUT", "POST"]:
        if request.path.rstrip('/').endswith('/delete'):
            return api_category_delete(request, category_id)
        return api_category_update(request, category_id)
    elif request.method == "DELETE":
        return api_category_delete(request, category_id)
    return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)


# =============================================================================
# Product Management REST APIs (Vendor / Merchant / Admin)
# =============================================================================

def _normalize_product_status(raw_status):
    if not raw_status:
        return 'ACTIVE'
    s = str(raw_status).strip().upper()
    if s in ['ACTIVE', 'ACT', 'TRUE', '1', 'ENABLE', 'ENABLED', 'AVAILABLE']:
        return 'ACTIVE'
    elif s in ['INACTIVE', 'INACT', 'DISABLED', 'DISABLE', 'FALSE', '0', 'HIDDEN']:
        return 'INACTIVE'
    elif s in ['OUT_OF_STOCK', 'OUTOFSTOCK', 'OUT OF STOCK', 'SOLDOUT', 'SOLD_OUT', 'SOLD OUT']:
        return 'OUT_OF_STOCK'
    return 'ACTIVE'


def _resolve_vendor_for_product(request, data=None):
    """
    Resolves the vendor for product operations:
    1. Authorization Bearer token header or active session
    2. vendor_id or vendor_code from payload / query parameters
    3. Fallback to first existing active vendor profile for smooth developer/test experience
    """
    data = data or {}
    vendor = _get_authenticated_vendor(request)
    if vendor:
        return vendor

    vendor_id = data.get('vendor_id') or request.GET.get('vendor_id')
    if vendor_id:
        v = VendorProfile.objects.filter(id=vendor_id).first()
        if v:
            return v

    vendor_code = data.get('vendor_code') or request.GET.get('vendor_code')
    if vendor_code:
        v = VendorProfile.objects.filter(vendor_code__iexact=str(vendor_code).strip()).first()
        if v:
            return v

    fallback = VendorProfile.objects.first()
    if not fallback:
        user, _ = User.objects.get_or_create(username='default_vendor', defaults={'email': 'vendor@nainjyoti.com'})
        fallback = VendorProfile.objects.create(
            user=user,
            business_name='Primary Merchant Store',
            owner_name='Store Manager',
            phone='9876543210',
            status='APPROVED'
        )
    return fallback


def _resolve_product_category(category_id=None, category_name=None):
    """Helper to locate or auto-link Category master"""
    if category_id:
        cat = Category.objects.filter(id=category_id).first()
        if cat:
            return cat
    if category_name:
        name_clean = str(category_name).strip()
        if name_clean:
            cat = Category.objects.filter(name__iexact=name_clean).first()
            if not cat:
                cat = Category.objects.create(name=name_clean, status='ACTIVE')
            return cat
    return None


@csrf_exempt
def api_product_list(request):
    """
    API: List Products with Advanced Filtering
    Method: GET
    Query Filters:
      - vendor_id or vendor_code: filter by seller
      - category_id or category: filter by Category master
      - search: search keyword in product name, SKU, or description
      - status: ACTIVE, INACTIVE, OUT_OF_STOCK
      - min_price, max_price: price range filter
      - in_stock: true/false (stock_quantity > 0)
      - ordering: sort field (default: -created_at)
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    qs = Product.objects.all().select_related('vendor', 'category')

    # Strict multi-tenant vendor scoping on /api/vendor/ routes
    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
        qs = qs.filter(vendor=vendor)
    else:
        # If seller provides Bearer token on public/admin route, optionally scope to their products unless scope='all' is passed
        auth_vendor = _get_authenticated_vendor(request)
        scope = request.GET.get("scope", "").lower()
        if auth_vendor and scope != "all" and not request.GET.get("vendor_id") and not request.GET.get("vendor_code"):
            qs = qs.filter(vendor=auth_vendor)
        else:
            vendor_id = request.GET.get("vendor_id")
            if vendor_id:
                qs = qs.filter(vendor_id=vendor_id)
            vendor_code = request.GET.get("vendor_code")
            if vendor_code:
                qs = qs.filter(vendor__vendor_code__iexact=vendor_code.strip())

    # Category filter
    category_id = request.GET.get("category_id")
    if category_id:
        qs = qs.filter(category_id=category_id)
    category_name = request.GET.get("category")
    if category_name:
        qs = qs.filter(category__name__icontains=category_name.strip())

    # Status filter
    status_param = request.GET.get("status", "").strip()
    if status_param:
        qs = qs.filter(status=_normalize_product_status(status_param))

    # Search keyword
    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(sku__icontains=search) | Q(description__icontains=search))

    # Price range
    min_price = request.GET.get("min_price")
    if min_price:
        try:
            qs = qs.filter(price__gte=float(min_price))
        except ValueError:
            pass

    max_price = request.GET.get("max_price")
    if max_price:
        try:
            qs = qs.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # In stock filter
    in_stock = request.GET.get("in_stock", "").lower()
    if in_stock in ["true", "1", "yes"]:
        qs = qs.filter(stock_quantity__gt=0)
    elif in_stock in ["false", "0", "no"]:
        qs = qs.filter(stock_quantity=0)

    # Ordering
    ordering = request.GET.get("ordering", "-created_at")
    allowed_orderings = ["created_at", "-created_at", "price", "-price", "name", "-name", "stock_quantity", "-stock_quantity"]
    if ordering in allowed_orderings:
        qs = qs.order_by(ordering)

    products = [p.to_dict() for p in qs]

    return JsonResponse({
        "success": True,
        "count": len(products),
        "products": products
    }, status=200)


@csrf_exempt
def api_product_create(request):
    """
    API: Create a New Product (with Image Upload)
    Method: POST
    Content-Type: multipart/form-data or application/json
    Parameters:
      - name: string (required)
      - price: number (required)
      - category_id or category: int / string (master Category)
      - sku: string (optional, auto-generated if blank)
      - discount_price: number (optional)
      - stock_quantity: int (optional, default 0)
      - unit: string (optional, default 'Piece')
      - description: text (optional)
      - status: ACTIVE, INACTIVE, OUT_OF_STOCK (optional, default ACTIVE)
      - image: image file (optional, multipart file upload or base64)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
    else:
        vendor = None

    data = _parse_request_data(request)

    # Validate name
    name = str(data.get("name", "")).strip()
    if not name:
        return JsonResponse({"success": False, "message": "Product 'name' is required."}, status=400)

    # Validate price
    raw_price = data.get("price")
    if raw_price is None or str(raw_price).strip() == "":
        return JsonResponse({"success": False, "message": "Product 'price' is required."}, status=400)
    try:
        price = float(raw_price)
        if price < 0:
            return JsonResponse({"success": False, "message": "Product 'price' cannot be negative."}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "message": "Invalid price value."}, status=400)

    # Discount price
    discount_price = None
    raw_discount = data.get("discount_price")
    if raw_discount not in [None, ""]:
        try:
            discount_price = float(raw_discount)
            if discount_price < 0:
                return JsonResponse({"success": False, "message": "Product 'discount_price' cannot be negative."}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "message": "Invalid discount_price value."}, status=400)

    # Stock quantity
    stock_quantity = 0
    raw_stock = data.get("stock_quantity")
    if raw_stock not in [None, ""]:
        try:
            stock_quantity = int(raw_stock)
            if stock_quantity < 0:
                return JsonResponse({"success": False, "message": "Stock quantity cannot be negative."}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "message": "Invalid stock_quantity value."}, status=400)

    # SKU validation if provided
    sku = str(data.get("sku", "")).strip()
    if sku and Product.objects.filter(sku__iexact=sku).exists():
        return JsonResponse({"success": False, "message": f"Product with SKU '{sku}' already exists."}, status=400)

    # Vendor resolution
    if not vendor:
        vendor = _resolve_vendor_for_product(request, data)

    # Category resolution
    cat_id = data.get("category_id")
    cat_name = data.get("category")
    category = _resolve_product_category(category_id=cat_id, category_name=cat_name)

    unit = str(data.get("unit", "Piece")).strip() or "Piece"
    description = str(data.get("description", "")).strip()
    status_val = _normalize_product_status(data.get("status", "ACTIVE"))

    product = Product(
        vendor=vendor,
        category=category,
        name=name,
        price=price,
        discount_price=discount_price,
        stock_quantity=stock_quantity,
        unit=unit,
        description=description,
        status=status_val,
        is_approved=True
    )
    if sku:
        product.sku = sku

    # Handle image upload (multipart file or base64)
    if request.FILES.get("image"):
        product.image = request.FILES["image"]
    elif "image" in data and isinstance(data["image"], str) and data["image"].startswith("data:image"):
        try:
            fmt, imgstr = data["image"].split(";base64,")
            ext = fmt.split("/")[-1].split("+")[0]
            product.image = ContentFile(base64.b64decode(imgstr), name=f"{slugify(name)}_{random.randint(1000, 9999)}.{ext}")
        except Exception:
            pass

    raw_thresh = data.get("low_stock_threshold")
    if raw_thresh not in [None, ""]:
        try:
            val_th = int(raw_thresh)
            if val_th >= 0:
                product.low_stock_threshold = val_th
        except (ValueError, TypeError):
            pass

    product.save()

    # Create initial audit log if initial stock > 0
    if product.stock_quantity > 0:
        StockLog.objects.create(
            product=product,
            vendor=product.vendor,
            movement_type='RESTOCK',
            quantity_changed=product.stock_quantity,
            previous_stock=0,
            new_stock=product.stock_quantity,
            reason="Initial stock upon product creation"
        )

    return JsonResponse({
        "success": True,
        "message": "Product created successfully",
        "product": product.to_dict()
    }, status=201)


@csrf_exempt
def api_product_detail(request, product_id):
    """
    API: Get Product Details
    Method: GET
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    product = Product.objects.filter(id=product_id).select_related('vendor', 'category').first()
    if not product:
        return JsonResponse({
            "success": False,
            "message": f"Product with ID '{product_id}' not found."
        }, status=404)

    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
        perm_err = _check_vendor_ownership(vendor, product, action_name="view")
        if perm_err:
            return perm_err

    return JsonResponse({
        "success": True,
        "product": product.to_dict()
    }, status=200)


@csrf_exempt
def api_product_update(request, product_id):
    """
    API: Update Product Details (Supports Image Replacement)
    Method: POST or PUT
    Content-Type: multipart/form-data or application/json
    Parameters:
      - name, price, discount_price, stock_quantity, unit, description, status, category_id, category, sku, image
    """
    if request.method not in ["POST", "PUT"]:
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST or PUT."}, status=405)

    product = Product.objects.filter(id=product_id).select_related('vendor', 'category').first()
    if not product:
        return JsonResponse({
            "success": False,
            "message": f"Product with ID '{product_id}' not found."
        }, status=404)

    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
        perm_err = _check_vendor_ownership(vendor, product, action_name="modify")
        if perm_err:
            return perm_err

    data = _parse_request_data(request)

    # Update name
    if "name" in data and str(data["name"]).strip():
        product.name = str(data["name"]).strip()

    # Update price
    if "price" in data and data["price"] not in [None, ""]:
        try:
            val = float(data["price"])
            if val < 0:
                return JsonResponse({"success": False, "message": "Product 'price' cannot be negative."}, status=400)
            product.price = val
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "message": "Invalid price value."}, status=400)

    # Update discount price
    if "discount_price" in data:
        raw_disc = data["discount_price"]
        if raw_disc in [None, "", "null"]:
            product.discount_price = None
        else:
            try:
                val = float(raw_disc)
                if val < 0:
                    return JsonResponse({"success": False, "message": "Product 'discount_price' cannot be negative."}, status=400)
                product.discount_price = val
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "message": "Invalid discount_price value."}, status=400)

    # Update stock quantity (with audit log)
    if "stock_quantity" in data and data["stock_quantity"] not in [None, ""]:
        try:
            val = int(data["stock_quantity"])
            if val < 0:
                return JsonResponse({"success": False, "message": "Stock quantity cannot be negative."}, status=400)
            if val != product.stock_quantity:
                prev_st = product.stock_quantity
                product.stock_quantity = val
                StockLog.objects.create(
                    product=product,
                    vendor=product.vendor,
                    movement_type='CORRECTION',
                    quantity_changed=val - prev_st,
                    previous_stock=prev_st,
                    new_stock=val,
                    reason="Stock updated via product edit form"
                )
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "message": "Invalid stock_quantity value."}, status=400)

    # Update low stock threshold
    if "low_stock_threshold" in data and data["low_stock_threshold"] not in [None, ""]:
        try:
            val_th = int(data["low_stock_threshold"])
            if val_th >= 0:
                product.low_stock_threshold = val_th
        except (ValueError, TypeError):
            pass

    # Update unit
    if "unit" in data and str(data["unit"]).strip():
        product.unit = str(data["unit"]).strip()

    # Update description
    if "description" in data:
        product.description = str(data["description"]).strip()

    # Update status
    if "status" in data and data["status"]:
        product.status = _normalize_product_status(data["status"])

    # Update SKU
    if "sku" in data and str(data["sku"]).strip():
        new_sku = str(data["sku"]).strip()
        if Product.objects.filter(sku__iexact=new_sku).exclude(pk=product.pk).exists():
            return JsonResponse({"success": False, "message": f"Another product with SKU '{new_sku}' already exists."}, status=400)
        product.sku = new_sku

    # Update category
    if "category_id" in data or "category" in data:
        cat_id = data.get("category_id")
        cat_name = data.get("category")
        category = _resolve_product_category(category_id=cat_id, category_name=cat_name)
        if category:
            product.category = category

    # Update image
    if request.FILES.get("image"):
        product.image = request.FILES["image"]
    elif "image" in data and isinstance(data["image"], str) and data["image"].startswith("data:image"):
        try:
            fmt, imgstr = data["image"].split(";base64,")
            ext = fmt.split("/")[-1].split("+")[0]
            product.image = ContentFile(base64.b64decode(imgstr), name=f"{slugify(product.name)}_{random.randint(1000, 9999)}.{ext}")
        except Exception:
            pass

    product.save()

    return JsonResponse({
        "success": True,
        "message": "Product updated successfully",
        "product": product.to_dict()
    }, status=200)


@csrf_exempt
def api_product_delete(request, product_id):
    """
    API: Delete Product
    Method: POST or DELETE
    """
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST or DELETE."}, status=405)

    product = Product.objects.filter(id=product_id).first()
    if not product:
        return JsonResponse({
            "success": False,
            "message": f"Product with ID '{product_id}' not found."
        }, status=404)

    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
        perm_err = _check_vendor_ownership(vendor, product, action_name="delete")
        if perm_err:
            return perm_err

    prod_name = product.name
    prod_sku = product.sku
    prod_id = product.id
    product.delete()

    return JsonResponse({
        "success": True,
        "message": f"Product '{prod_name}' ({prod_sku}) deleted successfully.",
        "product_id": prod_id
    }, status=200)


# REST alias wrappers for product list/create and detail/update/delete
@csrf_exempt
def api_product_list_create(request):
    if request.method == "GET":
        return api_product_list(request)
    elif request.method == "POST":
        return api_product_create(request)
    return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)


@csrf_exempt
def api_product_detail_update_delete(request, product_id):
    if request.method == "GET":
        return api_product_detail(request, product_id=product_id)
    elif request.method in ["PUT", "POST"]:
        if request.path.rstrip('/').endswith('/delete'):
            return api_product_delete(request, product_id)
        return api_product_update(request, product_id)
    elif request.method == "DELETE":
        return api_product_delete(request, product_id)
    return JsonResponse({"success": False, "message": "Method not allowed."}, status=405)


# =============================================================================
# Stock / Inventory Management REST APIs (Vendor / Merchant / Admin)
# =============================================================================

@csrf_exempt
def api_stock_summary(request):
    """
    API: Retrieve Inventory Stock Summary & KPI Cards
    Method: GET
    Returns: Total SKUs, total units, healthy stock, low stock count, out of stock count, total valuation
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    qs = Product.objects.all().select_related('vendor', 'category')
    
    # Strict multi-tenant vendor scoping on /api/vendor/ routes
    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
        qs = qs.filter(vendor=vendor)
    else:
        auth_vendor = _get_authenticated_vendor(request)
        scope = request.GET.get("scope", "").lower()
        if auth_vendor and scope != "all" and not request.GET.get("vendor_id") and not request.GET.get("vendor_code"):
            qs = qs.filter(vendor=auth_vendor)
        else:
            vendor_id = request.GET.get("vendor_id")
            if vendor_id:
                qs = qs.filter(vendor_id=vendor_id)
            vendor_code = request.GET.get("vendor_code")
            if vendor_code:
                qs = qs.filter(vendor__vendor_code__iexact=vendor_code.strip())

    total_skus = qs.count()
    total_units = 0
    healthy_count = 0
    low_stock_count = 0
    out_of_stock_count = 0
    total_valuation = 0.0

    for prod in qs:
        qty = max(prod.stock_quantity, 0)
        total_units += qty
        total_valuation += float(prod.price) * qty
        status = prod.stock_status
        if status == 'HEALTHY':
            healthy_count += 1
        elif status == 'LOW_STOCK':
            low_stock_count += 1
        elif status == 'OUT_OF_STOCK':
            out_of_stock_count += 1

    return JsonResponse({
        "success": True,
        "summary": {
            "total_skus": total_skus,
            "total_units": total_units,
            "healthy_count": healthy_count,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "total_valuation": round(total_valuation, 2),
            "currency": "INR"
        }
    }, status=200)


@csrf_exempt
def api_stock_list(request):
    """
    API: List Inventory & Stock Levels
    Method: GET
    Query Filters:
      - level: 'all', 'low_stock', 'out_of_stock', 'healthy'
      - category_id: filter by Category master
      - search: filter by product name or SKU
      - ordering: '-stock_quantity', 'stock_quantity', '-price', 'price'
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    qs = Product.objects.all().select_related('vendor', 'category')

    # Strict multi-tenant vendor scoping on /api/vendor/ routes
    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
        qs = qs.filter(vendor=vendor)
    else:
        auth_vendor = _get_authenticated_vendor(request)
        scope = request.GET.get("scope", "").lower()
        if auth_vendor and scope != "all" and not request.GET.get("vendor_id") and not request.GET.get("vendor_code"):
            qs = qs.filter(vendor=auth_vendor)
        else:
            vendor_id = request.GET.get("vendor_id")
            if vendor_id:
                qs = qs.filter(vendor_id=vendor_id)
            vendor_code = request.GET.get("vendor_code")
            if vendor_code:
                qs = qs.filter(vendor__vendor_code__iexact=vendor_code.strip())

    category_id = request.GET.get("category_id")
    if category_id:
        qs = qs.filter(category_id=category_id)

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(sku__icontains=search))

    level = request.GET.get("level", "").strip().lower()
    ordering = request.GET.get("ordering", "-created_at")

    if ordering in ["created_at", "-created_at", "price", "-price", "name", "-name", "stock_quantity", "-stock_quantity"]:
        qs = qs.order_by(ordering)

    items = []
    for prod in qs:
        st_status = prod.stock_status
        if level in ["low_stock", "low"] and st_status != "LOW_STOCK":
            continue
        if level in ["out_of_stock", "out"] and st_status != "OUT_OF_STOCK":
            continue
        if level in ["healthy", "normal"] and st_status != "HEALTHY":
            continue

        items.append({
            "product_id": prod.id,
            "name": prod.name,
            "sku": prod.sku,
            "category_id": prod.category_id,
            "category_name": prod.category.name if prod.category else None,
            "vendor_id": prod.vendor_id,
            "vendor_name": prod.vendor.business_name if prod.vendor else None,
            "price": float(prod.price),
            "stock_quantity": prod.stock_quantity,
            "low_stock_threshold": prod.low_stock_threshold,
            "stock_status": st_status,
            "stock_valuation": prod.stock_valuation,
            "unit": prod.unit,
            "image": prod.image_url,
            "last_updated": prod.updated_at.isoformat() if prod.updated_at else None,
        })

    return JsonResponse({
        "success": True,
        "count": len(items),
        "inventory": items
    }, status=200)


@csrf_exempt
def api_stock_update(request, product_id):
    """
    API: Adjust Inventory Stock (with Audit Logging)
    Method: POST or PUT
    Params:
      - action: 'ADD' (Restock), 'SUBTRACT' (Damage/Deduction), or 'SET' (Physical recount)
      - quantity: integer (units to add/subtract or target quantity)
      - movement_type: 'RESTOCK', 'SALE', 'RETURN', 'DAMAGE', 'CORRECTION' (optional)
      - reason: string (optional, notes/explanation)
      - reference_id: string (optional, PO # or Order #)
      - low_stock_threshold: int (optional, update reorder threshold)
    """
    if request.method not in ["POST", "PUT"]:
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST or PUT."}, status=405)

    product = Product.objects.filter(id=product_id).select_related('vendor', 'category').first()
    if not product:
        return JsonResponse({"success": False, "message": f"Product with ID '{product_id}' not found."}, status=404)

    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
        perm_err = _check_vendor_ownership(vendor, product, action_name="adjust stock for")
        if perm_err:
            return perm_err

    data = _parse_request_data(request)

    action = str(data.get("action", "ADD")).strip().upper()
    if action not in ["ADD", "SUBTRACT", "SET"]:
        return JsonResponse({"success": False, "message": "Invalid action. Use 'ADD', 'SUBTRACT', or 'SET'."}, status=400)

    raw_qty = data.get("quantity")
    if raw_qty is None or str(raw_qty).strip() == "":
        return JsonResponse({"success": False, "message": "Field 'quantity' is required."}, status=400)

    try:
        qty = int(raw_qty)
        if action in ["ADD", "SUBTRACT"] and qty <= 0:
            return JsonResponse({"success": False, "message": f"Quantity for {action} must be greater than 0."}, status=400)
        elif action == "SET" and qty < 0:
            return JsonResponse({"success": False, "message": "Quantity for SET cannot be negative."}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "message": "Quantity must be a valid integer."}, status=400)

    prev_stock = product.stock_quantity

    if action == "ADD":
        new_stock = prev_stock + qty
        qty_changed = qty
        default_movement = "RESTOCK"
    elif action == "SUBTRACT":
        if qty > prev_stock:
            return JsonResponse({
                "success": False,
                "message": f"Cannot subtract {qty} units. Current stock is only {prev_stock} units."
            }, status=400)
        new_stock = prev_stock - qty
        qty_changed = -qty
        default_movement = "DAMAGE"
    elif action == "SET":
        new_stock = qty
        qty_changed = new_stock - prev_stock
        default_movement = "CORRECTION"

    raw_mv = str(data.get("movement_type", "")).strip().upper()
    valid_movements = ["RESTOCK", "SALE", "RETURN", "DAMAGE", "CORRECTION"]
    movement_type = raw_mv if raw_mv in valid_movements else default_movement

    reason = str(data.get("reason", "")).strip()
    if not reason:
        reason = f"Inventory {action.lower()} of {abs(qty_changed)} units via console"

    reference_id = str(data.get("reference_id", "")).strip()

    raw_thresh = data.get("low_stock_threshold")
    if raw_thresh not in [None, ""]:
        try:
            val_th = int(raw_thresh)
            if val_th >= 0:
                product.low_stock_threshold = val_th
        except (ValueError, TypeError):
            pass

    product.stock_quantity = new_stock
    product.save()

    stock_log = StockLog.objects.create(
        product=product,
        vendor=product.vendor,
        movement_type=movement_type,
        quantity_changed=qty_changed,
        previous_stock=prev_stock,
        new_stock=new_stock,
        reason=reason,
        reference_id=reference_id
    )

    return JsonResponse({
        "success": True,
        "message": f"Stock for '{product.name}' adjusted from {prev_stock} to {new_stock} units.",
        "product": product.to_dict(),
        "log": stock_log.to_dict()
    }, status=200)


@csrf_exempt
def api_stock_logs(request, product_id=None):
    """
    API: Retrieve Inventory Movement Audit Logs
    Method: GET
    Query Filters:
      - product_id: (in path or query)
      - movement_type: RESTOCK, SALE, RETURN, DAMAGE, CORRECTION
      - limit: default 50
    """
    if request.method != "GET":
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    qs = StockLog.objects.all().select_related('product', 'vendor')

    prod_id = product_id or request.GET.get("product_id")

    # Strict multi-tenant vendor scoping on /api/vendor/ routes
    if request.path.startswith('/api/vendor/'):
        vendor, err_resp = _require_vendor_auth(request)
        if err_resp:
            return err_resp
        qs = qs.filter(vendor=vendor)
        if prod_id:
            target_prod = Product.objects.filter(id=prod_id).first()
            if target_prod and target_prod.vendor_id != vendor.id:
                return JsonResponse({
                    "success": False,
                    "message": "Access denied. You do not have permission to view stock logs for this product."
                }, status=403)
            qs = qs.filter(product_id=prod_id)
    else:
        if prod_id:
            qs = qs.filter(product_id=prod_id)

        auth_vendor = _get_authenticated_vendor(request)
        scope = request.GET.get("scope", "").lower()
        if auth_vendor and scope != "all" and not request.GET.get("vendor_id") and not request.GET.get("vendor_code"):
            qs = qs.filter(vendor=auth_vendor)
        else:
            vendor_id = request.GET.get("vendor_id")
            if vendor_id:
                qs = qs.filter(vendor_id=vendor_id)
            vendor_code = request.GET.get("vendor_code")
            if vendor_code:
                qs = qs.filter(vendor__vendor_code__iexact=vendor_code.strip())

    movement_type = request.GET.get("movement_type", "").strip().upper()
    if movement_type:
        qs = qs.filter(movement_type=movement_type)

    limit = 50
    if request.GET.get("limit"):
        try:
            limit = max(1, min(int(request.GET.get("limit")), 200))
        except (ValueError, TypeError):
            pass

    logs = [log.to_dict() for log in qs[:limit]]

    return JsonResponse({
        "success": True,
        "count": len(logs),
        "logs": logs
    }, status=200)





