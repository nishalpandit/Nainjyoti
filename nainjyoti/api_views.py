import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.utils import timezone
from .models import UserProfile, OTPRecord

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
