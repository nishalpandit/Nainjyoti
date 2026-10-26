import json

import base64

import random

import secrets

import hashlib

import hmac

from functools import wraps
from decimal import Decimal, InvalidOperation

from datetime import datetime, timedelta

from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.models import User

from django.contrib.auth import login, logout, authenticate

from django.db import transaction

from django.db.models import Q, Sum, Count, Avg, Min, DecimalField

from django.db.models.functions import Coalesce

from django.utils import timezone

from django.utils.text import slugify

from django.core.files.base import ContentFile

from django.conf import settings

from .models import (
    UserProfile, UserAddress, OTPRecord, VendorProfile, Category, Banner, Product, ProductVariant, CartItem, WishlistItem,

    ProductReview, StockLog, Order, PaymentTransaction, OrderItem, OrderRequest, Notification,

    OrderStatusHistory, VendorEarning, VendorPayout, CommissionSetting,

    commission_amount_for, customer_price_for

)


def _customer_variant_dict(variant, commission_rate=None):
    """Serialize a variant with customer-payable prices in the standard price fields."""
    rate = commission_rate if commission_rate is not None else CommissionSetting.current_rate()
    data = variant.to_dict()
    base_regular = variant.price if variant.price is not None else variant.product.price
    if variant.discount_price is not None:
        base_discount = variant.discount_price
    elif variant.price is None and variant.product.discount_price is not None:
        base_discount = variant.product.discount_price
    else:
        base_discount = None
    base_effective = Decimal(str(variant.effective_price))
    data.update({
        'price': float(customer_price_for(base_regular, rate)),
        'discount_price': float(customer_price_for(base_discount, rate)) if base_discount is not None else None,
        'effective_price': float(customer_price_for(base_effective, rate)),
        'commission_rate_percent': float(rate),
        'commission_amount': float(commission_amount_for(base_effective, rate)),
    })
    return data


def admin_api_required(view_func):
    """Require an active Django staff session for every /api/admin/ endpoint."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({
                "success": False,
                "message": "Administrator authentication is required.",
            }, status=401)
        if not user.is_active or not (user.is_staff or user.is_superuser):
            return JsonResponse({
                "success": False,
                "message": "Administrator permission is required.",
            }, status=403)
        return view_func(request, *args, **kwargs)

    return wrapped


def _populate_multipart_request(request):
    """
    Ensure request._post and request._files are properly populated for PUT/PATCH,
    or requests where Content-Type was overridden in headers (e.g. application/json in Postman),
    or where Django did not populate request.POST and request.FILES.
    """
    content_type = request.content_type or request.META.get('CONTENT_TYPE', '') or ''
    raw_body = b''
    try:
        raw_body = request.body
    except Exception:
        pass

    is_multipart = 'multipart/form-data' in content_type
    looks_like_multipart = bool(raw_body and raw_body.startswith(b'--'))

    if is_multipart or looks_like_multipart:
        curr_files = getattr(request, '_files', None)
        curr_post = getattr(request, '_post', None)
        if (curr_files and len(curr_files) > 0) or (curr_post and len(curr_post) > 0):
            if is_multipart and not looks_like_multipart:
                return
            if not looks_like_multipart:
                return

        try:
            from io import BytesIO
            from django.http.multipartparser import MultiPartParser
            meta = request.META.copy()
            meta['CONTENT_LENGTH'] = str(len(raw_body))

            if not is_multipart and looks_like_multipart:
                first_line = raw_body.split(b'\r\n')[0]
                if first_line.startswith(b'--'):
                    boundary_val = first_line[2:].rstrip(b'\r\n- ').decode('latin1', errors='ignore')
                else:
                    boundary_val = first_line.rstrip(b'\r\n- ').decode('latin1', errors='ignore')
                meta['CONTENT_TYPE'] = f"multipart/form-data; boundary={boundary_val}"
            elif is_multipart and 'boundary=' not in content_type and looks_like_multipart:
                first_line = raw_body.split(b'\r\n')[0]
                if first_line.startswith(b'--'):
                    boundary_val = first_line[2:].rstrip(b'\r\n- ').decode('latin1', errors='ignore')
                else:
                    boundary_val = first_line.rstrip(b'\r\n- ').decode('latin1', errors='ignore')
                meta['CONTENT_TYPE'] = f"multipart/form-data; boundary={boundary_val}"

            stream = BytesIO(raw_body)
            parser = MultiPartParser(meta, stream, request.upload_handlers, request.encoding)
            post_data, files_data = parser.parse()
            if post_data or files_data:
                request._post = post_data
                request._files = files_data
        except Exception:
            pass


def _parse_request_data(request):
    """Helper to extract data from JSON body, POST form data, or PUT/PATCH body."""
    _populate_multipart_request(request)

    content_type = request.content_type or request.META.get('CONTENT_TYPE', '') or ''
    try:
        raw_body = request.body
    except Exception:
        raw_body = b''

    if ('multipart/form-data' in content_type) or (raw_body and raw_body.startswith(b'--')):
        if hasattr(request, 'POST') and request.POST:
            return request.POST.dict()
        if getattr(request, '_post', None):
            return request._post.dict()
        return {}

    if 'application/json' in content_type:
        try:
            return json.loads(raw_body.decode('utf-8'))
        except Exception:
            return {}

    if request.method in ('PUT', 'PATCH') and 'application/x-www-form-urlencoded' in content_type:
        from django.http import QueryDict
        return QueryDict(raw_body).dict()

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

    existing_profile = UserProfile.objects.filter(phone=phone).first()

    if existing_profile and (not existing_profile.is_active or (existing_profile.user and not existing_profile.user.is_active)):

        return JsonResponse({

            "success": False,

            "message": "Your account has been deactivated by administrator. Please contact support."

        }, status=403)



    is_registered = existing_profile is not None

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

        # Check if deactivated by admin

        if not profile.is_active or (profile.user and not profile.user.is_active):

            return JsonResponse({

                "success": False,

                "message": "Your account has been deactivated by administrator. Please contact support."

            }, status=403)



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
      - password (optional)
      - dob (optional, YYYY-MM-DD)
      - gender (Male/Female/Other/Prefer not to say)
      - profile_photo (file, base64, or binary, optional)
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)

    _populate_multipart_request(request)
    data = _parse_request_data(request)

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    phone = str(data.get("phone", "")).strip().replace(" ", "").replace("-", "")
    email = data.get("email", "").strip().lower() or None
    dob_raw = data.get("dob", "").strip()
    gender = data.get("gender", "Prefer not to say").strip()

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

    # Check if email is already in use
    if email and User.objects.filter(email=email).exists():
        return JsonResponse({
            "success": False,
            "message": "This email address is already in use by another account."
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
    password = data.get("password", "").strip()
    if password:
        user.set_password(password)
    else:
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
        is_active=True
    )

    # Save uploaded profile photo if provided
    _save_profile_photo_from_request(request, profile, data)

    if hasattr(request, 'session'):
        login(request, user)

    return JsonResponse({
        "success": True,
        "message": "User registered successfully",
        "token": profile.auth_token,
        "user": profile.to_dict()
    }, status=201)


@csrf_exempt

def api_user_login(request):

    """

    API: Direct Password Login for Registered User (Phone or Email)

    Endpoint: POST /api/user/login/

    Body: {"identifier": "9876543210" or "user@example.com", "password": "your_password"}

    """

    if request.method != "POST":

        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)



    data = _parse_request_data(request)

    identifier = str(data.get("identifier", "") or data.get("phone", "") or data.get("email", "")).strip()

    password = str(data.get("password", "")).strip()



    if not identifier or not password:

        return JsonResponse({

            "success": False,

            "message": "Both 'identifier' (phone or email) and 'password' are required."

        }, status=400)



    clean_phone = identifier.replace(" ", "").replace("-", "")

    profile = UserProfile.objects.filter(

        Q(phone=clean_phone) | Q(email__iexact=identifier) | Q(user__username__iexact=identifier)

    ).first()



    if not profile:

        return JsonResponse({

            "success": False,

            "message": "No registered account found matching the provided phone number or email."

        }, status=404)



    # Check if deactivated by admin

    if not profile.is_active or (profile.user and not profile.user.is_active):

        return JsonResponse({

            "success": False,

            "message": "Your account has been deactivated by administrator. Please contact support."

        }, status=403)



    # Check password

    if not profile.user.check_password(password):

        return JsonResponse({

            "success": False,

            "message": "Invalid password. Please check your credentials or sign in with OTP."

        }, status=400)



    if not profile.auth_token:

        profile.generate_new_token()



    if hasattr(request, 'session'):

        login(request, profile.user)



    return JsonResponse({

        "success": True,

        "message": "Login successful",

        "token": profile.auth_token,

        "user": profile.to_dict()

    }, status=200)





@csrf_exempt

def api_user_status(request):

    """

    API: Check User Authentication Status & Admin Account Health

    Endpoint: GET /api/user/status/

    Header: Authorization: Bearer <token>

    """

    auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')

    token = ''

    if auth_header:

        parts = auth_header.split()

        if len(parts) == 2 and parts[0].lower() in ['bearer', 'token']:

            token = parts[1].strip()



    if not token and request.user.is_authenticated and hasattr(request.user, 'customer_profile'):

        profile = request.user.customer_profile

    elif token:

        # Check without is_active filter first to provide accurate feedback if deactivated

        profile = UserProfile.objects.filter(auth_token=token).first()

    else:

        profile = None



    if not profile:

        return JsonResponse({

            "success": False,

            "authenticated": False,

            "message": "Invalid or missing authentication token."

        }, status=401)



    if not profile.is_active or (profile.user and not profile.user.is_active):

        return JsonResponse({

            "success": False,

            "authenticated": False,

            "is_active": False,

            "message": "Your account has been deactivated by administrator. Please contact support."

        }, status=403)



    return JsonResponse({

        "success": True,

        "authenticated": True,

        "is_active": True,

        "user": profile.to_dict()

    }, status=200)





def _save_profile_photo_from_request(request, profile, data=None):
    """
    Extracts and attaches profile photo to a UserProfile from:
      1. request.FILES (keys: profile_photo, photo, image, avatar, profile_image, file, picture, user_photo, img, or first file)
      2. remove_photo: true flag
      3. Raw binary body (image/* or application/octet-stream)
      4. Base64 data URI or raw base64 string in data
      5. Local filesystem path or media filename in data
    Saves and persists to profile.profile_photo.
    """
    import os
    if data is None:
        data = _parse_request_data(request)

    # 1. Check remove_photo
    if str(data.get("remove_photo", "")).lower() in ["true", "1", "yes"]:
        profile.profile_photo = None
        profile.save(update_fields=['profile_photo'])
        return True

    # 2. Check uploaded file in request.FILES
    photo_file = None
    if request.FILES:
        for key in ("profile_photo", "photo", "image", "avatar", "profile_image", "file", "picture", "user_photo", "img"):
            if key in request.FILES:
                photo_file = request.FILES[key]
                break
        if not photo_file:
            photo_file = next(iter(request.FILES.values()), None)

    if photo_file:
        if hasattr(photo_file, 'seek'):
            try:
                photo_file.seek(0)
            except Exception:
                pass
        ext = os.path.splitext(getattr(photo_file, 'name', '') or '')[1].lower()
        if not ext or ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            ext = '.png'
        file_name = f"user_{profile.id}_{secrets.token_hex(4)}{ext}"
        try:
            file_bytes = photo_file.read()
            profile.profile_photo.save(file_name, ContentFile(file_bytes), save=False)
        except Exception:
            profile.profile_photo = photo_file
        profile.save(update_fields=['profile_photo'])
        return True

    # 3. Check raw binary body
    content_type = request.content_type or request.META.get('CONTENT_TYPE', '') or ''
    if (content_type.startswith('image/') or content_type == 'application/octet-stream') and request.body and len(request.body) > 100:
        ext = '.jpg' if 'jpeg' in content_type else ('.png' if 'png' in content_type else '.jpg')
        file_name = f"user_{profile.id}_{secrets.token_hex(4)}{ext}"
        profile.profile_photo.save(file_name, ContentFile(request.body), save=False)
        profile.save(update_fields=['profile_photo'])
        return True

    # 4. Check base64 string or filename in data
    raw_photo = None
    for key in ("profile_photo", "profile_photo_base64", "photo", "image", "avatar", "profile_image", "file", "picture"):
        if key in data and data[key]:
            raw_photo = data[key]
            break

    if raw_photo and isinstance(raw_photo, str):
        raw_photo_str = raw_photo.strip()
        # (A) Base64 string
        if "base64," in raw_photo_str or (len(raw_photo_str) > 100 and not raw_photo_str.startswith("http") and not raw_photo_str.startswith("/")):
            b64_str = raw_photo_str.split(",", 1)[1] if "," in raw_photo_str else raw_photo_str
            try:
                img_data = base64.b64decode(b64_str)
                file_name = f"user_{profile.id}_{secrets.token_hex(4)}.png"
                profile.profile_photo.save(file_name, ContentFile(img_data), save=False)
                profile.save(update_fields=['profile_photo'])
                return True
            except Exception:
                pass
        # (B) Absolute path on local filesystem
        elif os.path.isabs(raw_photo_str) and os.path.exists(raw_photo_str) and os.path.isfile(raw_photo_str):
            try:
                with open(raw_photo_str, "rb") as f_local:
                    file_name = f"user_{profile.id}_{secrets.token_hex(4)}_{os.path.basename(raw_photo_str)}"
                    profile.profile_photo.save(file_name, ContentFile(f_local.read()), save=False)
                    profile.save(update_fields=['profile_photo'])
                    return True
            except Exception:
                pass
        # (C) Relative filename or media path (ignore placeholders like '<binary file optional>')
        elif raw_photo_str and not raw_photo_str.startswith("<"):
            clean_name = raw_photo_str.replace("/media/", "").replace("media/", "").strip("/\\")
            direct_path = os.path.join(settings.MEDIA_ROOT, clean_name)
            photo_dir = os.path.join(settings.MEDIA_ROOT, "user_profiles", "photos")
            sub_path = os.path.join(photo_dir, os.path.basename(clean_name))
            if os.path.exists(direct_path) and os.path.isfile(direct_path):
                profile.profile_photo.name = clean_name
                profile.save(update_fields=['profile_photo'])
                return True
            elif os.path.exists(sub_path) and os.path.isfile(sub_path):
                profile.profile_photo.name = f"user_profiles/photos/{os.path.basename(clean_name)}"
                profile.save(update_fields=['profile_photo'])
                return True

    return False


def _handle_profile_update(request, profile):
    """Internal helper to process profile field updates, email conflicts, and photo updates."""
    _populate_multipart_request(request)
    data = _parse_request_data(request)

    # 1. Update text fields
    if "first_name" in data and str(data["first_name"]).strip():
        profile.first_name = str(data["first_name"]).strip()
        profile.user.first_name = profile.first_name

    if "last_name" in data and str(data["last_name"]).strip():
        profile.last_name = str(data["last_name"]).strip()
        profile.user.last_name = profile.last_name

    if "email" in data:
        new_email = str(data["email"]).strip().lower() or None
        if new_email and new_email != profile.email:
            if User.objects.filter(email=new_email).exclude(id=profile.user.id).exists():
                return JsonResponse({
                    "success": False,
                    "message": "This email address is already in use by another account."
                }, status=400)
        profile.email = new_email
        profile.user.email = new_email or ""

    if "gender" in data:
        valid_genders = ['Male', 'Female', 'Other', 'Prefer not to say']
        gender_val = str(data["gender"]).strip()
        if gender_val in valid_genders:
            profile.gender = gender_val

    if "dob" in data and data["dob"]:
        dob_str = str(data["dob"]).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                profile.dob = datetime.strptime(dob_str, fmt).date()
                break
            except ValueError:
                continue

    profile.user.save()
    profile.save()

    # 2. Update photo if provided
    _save_profile_photo_from_request(request, profile, data)

    res_user = profile.to_dict()
    res_user['total_orders'] = profile.orders.count()
    res_user['total_spent'] = float(profile.orders.exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0)

    return JsonResponse({
        "success": True,
        "message": "Profile updated successfully",
        "user": res_user
    }, status=200)


@csrf_exempt

def api_user_profile(request):

    """

    API: Get Authenticated User Profile

    Endpoint: GET /api/user/profile/ (or PUT/POST for profile updates)

    Header: Authorization: Bearer <token>

    """

    auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')

    token = ''

    if auth_header:

        parts = auth_header.split()

        if len(parts) == 2 and parts[0].lower() in ['bearer', 'token']:

            token = parts[1].strip()



    if token:

        raw_profile = UserProfile.objects.filter(auth_token=token).first()

        if raw_profile and (not raw_profile.is_active or (raw_profile.user and not raw_profile.user.is_active)):

            return JsonResponse({

                "success": False,

                "message": "Your account has been deactivated by administrator. Please contact support."

            }, status=403)



    profile = _get_authenticated_profile(request)

    if not profile:

        return JsonResponse({

            "success": False,

            "message": "Authentication required. Pass valid Bearer token in 'Authorization' header."

        }, status=401)



    if request.method == "GET":

        data = profile.to_dict()

        data["total_orders"] = profile.orders.count()

        data["total_spent"] = float(profile.orders.exclude(status='CANCELLED').aggregate(t=Sum('total_amount'))['t'] or 0.0)

        return JsonResponse({

            "success": True,

            "user": data

        }, status=200)



    elif request.method in ["POST", "PUT"]:

        return _handle_profile_update(request, profile)



    return JsonResponse({"success": False, "message": "Method not allowed. Use GET, POST, or PUT."}, status=405)





@csrf_exempt

def api_user_profile_update(request):

    """

    API: Dedicated Profile Update Endpoint

    Endpoint: PUT or POST /api/user/profile/update/

    Header: Authorization: Bearer <token>

    """

    auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')

    token = ''

    if auth_header:

        parts = auth_header.split()

        if len(parts) == 2 and parts[0].lower() in ['bearer', 'token']:

            token = parts[1].strip()



    if token:

        raw_profile = UserProfile.objects.filter(auth_token=token).first()

        if raw_profile and (not raw_profile.is_active or (raw_profile.user and not raw_profile.user.is_active)):

            return JsonResponse({

                "success": False,

                "message": "Your account has been deactivated by administrator. Please contact support."

            }, status=403)



    profile = _get_authenticated_profile(request)

    if not profile:

        return JsonResponse({

            "success": False,

            "message": "Authentication required. Pass valid Bearer token in 'Authorization' header."

        }, status=401)



    if request.method not in ["POST", "PUT"]:

        return JsonResponse({"success": False, "message": "Method not allowed. Use POST or PUT."}, status=405)



    return _handle_profile_update(request, profile)





@csrf_exempt

def api_user_profile_photo(request):
    """
    API: Upload, Update, or Remove User Profile Photo
    Endpoint: POST or PUT /api/user/profile/photo/
    Header: Authorization: Bearer <token>
    Content-Type: multipart/form-data (or application/json for base64/remove)
    Params:
      - profile_photo: [binary file]
      - remove_photo: true (optional, to remove profile photo)
    """
    auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')
    token = ''
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() in ['bearer', 'token']:
            token = parts[1].strip()

    if token:
        raw_profile = UserProfile.objects.filter(auth_token=token).first()
        if raw_profile and (not raw_profile.is_active or (raw_profile.user and not raw_profile.user.is_active)):
            return JsonResponse({
                "success": False,
                "message": "Your account has been deactivated by administrator. Please contact support."
            }, status=403)

    profile = _get_authenticated_profile(request)
    if not profile:
        return JsonResponse({
            "success": False,
            "message": "Authentication required. Pass valid Bearer token in 'Authorization' header."
        }, status=401)

    if request.method not in ["POST", "PUT"]:
        return JsonResponse({"success": False, "message": "Method not allowed. Use POST or PUT."}, status=405)

    _populate_multipart_request(request)
    data = _parse_request_data(request)

    # 1. Check if user wants to remove photo
    if str(data.get("remove_photo", "")).lower() in ["true", "1", "yes"]:
        profile.profile_photo = None
        profile.save(update_fields=['profile_photo'])
        return JsonResponse({
            "success": True,
            "message": "Profile photo removed successfully",
            "profile_photo": profile.photo_url,
            "user": profile.to_dict()
        }, status=200)

    # 2. Extract and save uploaded photo
    saved = _save_profile_photo_from_request(request, profile, data)
    if not saved and not profile.profile_photo:
        return JsonResponse({
            "success": False,
            "message": "No profile_photo file or valid image data was provided in the request."
        }, status=400)

    return JsonResponse({
        "success": True,
        "message": "Profile photo uploaded successfully",
        "profile_photo": profile.photo_url,
        "user": profile.to_dict()
    }, status=200)


def _require_user_auth(request):

    """Return the authenticated customer or a consistent API error response."""

    auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')

    parts = auth_header.split()

    if len(parts) == 2 and parts[0].lower() in ['bearer', 'token']:

        raw_profile = UserProfile.objects.select_related('user').filter(auth_token=parts[1].strip()).first()

        if raw_profile and (not raw_profile.is_active or not raw_profile.user.is_active):

            return None, JsonResponse({

                "success": False,

                "message": "Your account has been deactivated by administrator. Please contact support."

            }, status=403)



    profile = _get_authenticated_profile(request)

    if not profile:

        return None, JsonResponse({

            "success": False,

            "message": "Authentication required. Pass valid Bearer token in 'Authorization' header."

        }, status=401)

    return profile, None





def _parse_boolean(value):

    if isinstance(value, bool):

        return value, True

    normalized = str(value).strip().lower()

    if normalized in ['true', '1', 'yes', 'on']:

        return True, True

    if normalized in ['false', '0', 'no', 'off']:

        return False, True

    return False, False





def _clean_address_data(data, profile, partial=False):

    """Normalize and validate JSON or form-data used by address endpoints."""

    cleaned = {}

    errors = {}



    def supplied(*names):

        return next((name for name in names if name in data), None)



    field_aliases = {

        'address_line_1': ('address_line_1', 'address_line1', 'address'),

        'address_line_2': ('address_line_2', 'address_line2'),

        'pincode': ('pincode', 'postal_code'),

    }



    defaults = {

        'full_name': profile.full_name,

        'phone': profile.phone,

        'address_type': 'Home',

        'country': 'India',

        'address_line_2': '',

        'landmark': '',

    }



    for field in [

        'full_name', 'phone', 'address_type', 'address_line_1', 'address_line_2',

        'landmark', 'city', 'state', 'pincode', 'country',

    ]:

        names = field_aliases.get(field, (field,))

        source_name = supplied(*names)

        if source_name is not None:

            cleaned[field] = str(data.get(source_name, '')).strip()

        elif not partial and field in defaults:

            cleaned[field] = defaults[field]



    required_fields = {

        'full_name': 'Full name is required.',

        'phone': 'Phone number is required.',

        'address_line_1': 'Address line 1 is required.',

        'city': 'City is required.',

        'state': 'State is required.',

        'pincode': 'Pincode is required.',

        'country': 'Country is required.',

    }

    for field, message in required_fields.items():

        if (not partial or field in cleaned) and not cleaned.get(field):

            errors[field] = message



    if 'address_type' in cleaned:

        normalized_type = cleaned['address_type'].lower().capitalize()

        if normalized_type not in ['Home', 'Work', 'Other']:

            errors['address_type'] = "Address type must be Home, Work, or Other."

        else:

            cleaned['address_type'] = normalized_type



    if 'phone' in cleaned and cleaned['phone']:

        phone = cleaned['phone'].replace(' ', '').replace('-', '')

        phone_digits = phone[1:] if phone.startswith('+') else phone

        if not phone_digits.isdigit() or not 10 <= len(phone_digits) <= 15:

            errors['phone'] = 'Phone number must contain 10 to 15 digits.'

        else:

            cleaned['phone'] = phone



    if 'pincode' in cleaned and cleaned['pincode']:

        pincode = cleaned['pincode'].replace(' ', '')

        if not pincode.isdigit() or len(pincode) != 6:

            errors['pincode'] = 'Pincode must be exactly 6 digits.'

        else:

            cleaned['pincode'] = pincode



    if 'is_default' in data:

        is_default, is_valid = _parse_boolean(data['is_default'])

        if not is_valid:

            errors['is_default'] = 'is_default must be true or false.'

        else:

            cleaned['is_default'] = is_default



    return cleaned, errors





def _address_not_found_response():

    return JsonResponse({

        "success": False,

        "message": "Address not found."

    }, status=404)





@csrf_exempt

def api_user_address_create(request):

    """Create a saved delivery address for the authenticated user."""

    if request.method != 'POST':

        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    data = _parse_request_data(request)

    cleaned, errors = _clean_address_data(data, profile)

    if errors:

        return JsonResponse({

            "success": False,

            "message": "Please correct the address details.",

            "errors": errors,

        }, status=400)



    requested_default = cleaned.pop('is_default', False)

    with transaction.atomic():

        locked_profile = UserProfile.objects.select_for_update().get(pk=profile.pk)

        make_default = requested_default or not locked_profile.addresses.exists()

        if make_default:

            locked_profile.addresses.filter(is_default=True).update(is_default=False)

        address = UserAddress.objects.create(

            user=locked_profile,

            is_default=make_default,

            **cleaned,

        )



    return JsonResponse({

        "success": True,

        "message": "Address added successfully",

        "address": address.to_dict(),

    }, status=201)





@csrf_exempt

def api_user_address_list(request):

    """List every saved address owned by the authenticated user."""

    if request.method != 'GET':

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    addresses = list(profile.addresses.all())

    default_address = next((address for address in addresses if address.is_default), None)

    return JsonResponse({

        "success": True,

        "message": "Addresses fetched successfully",

        "count": len(addresses),

        "default_address_id": default_address.id if default_address else None,

        "addresses": [address.to_dict() for address in addresses],

    }, status=200)





@csrf_exempt

def api_user_address_detail(request, address_id):

    """Return one saved address owned by the authenticated user."""

    if request.method != 'GET':

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    address = profile.addresses.filter(pk=address_id).first()

    if not address:

        return _address_not_found_response()



    return JsonResponse({

        "success": True,

        "message": "Address fetched successfully",

        "address": address.to_dict(),

    }, status=200)





@csrf_exempt

def api_user_address_update(request, address_id):

    """Partially or fully update an address owned by the authenticated user."""

    if request.method not in ['POST', 'PUT', 'PATCH']:

        return JsonResponse({

            "success": False,

            "message": "Method not allowed. Use POST, PUT, or PATCH."

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    address = profile.addresses.filter(pk=address_id).first()

    if not address:

        return _address_not_found_response()



    data = _parse_request_data(request)

    cleaned, errors = _clean_address_data(data, profile, partial=True)

    if errors:

        return JsonResponse({

            "success": False,

            "message": "Please correct the address details.",

            "errors": errors,

        }, status=400)

    if not cleaned:

        return JsonResponse({

            "success": False,

            "message": "Provide at least one address field to update."

        }, status=400)



    requested_default = cleaned.pop('is_default', None)

    with transaction.atomic():

        address = UserAddress.objects.select_for_update().get(pk=address.pk, user=profile)

        for field, value in cleaned.items():

            setattr(address, field, value)

        if requested_default is True:

            profile.addresses.exclude(pk=address.pk).filter(is_default=True).update(is_default=False)

            address.is_default = True

        address.save()



    return JsonResponse({

        "success": True,

        "message": "Address updated successfully",

        "address": address.to_dict(),

    }, status=200)





@csrf_exempt

def api_user_address_set_default(request, address_id):

    """Make one of the authenticated user's saved addresses the default."""

    if request.method != 'POST':

        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    address = profile.addresses.filter(pk=address_id).first()

    if not address:

        return _address_not_found_response()



    with transaction.atomic():

        address = UserAddress.objects.select_for_update().get(pk=address.pk, user=profile)

        profile.addresses.exclude(pk=address.pk).filter(is_default=True).update(is_default=False)

        if not address.is_default:

            address.is_default = True

            address.save(update_fields=['is_default', 'updated_at'])



    return JsonResponse({

        "success": True,

        "message": "Default address updated successfully",

        "address": address.to_dict(),

    }, status=200)





@csrf_exempt

def api_user_address_delete(request, address_id):

    """Delete an address and promote another address when required."""

    if request.method not in ['DELETE', 'POST']:

        return JsonResponse({

            "success": False,

            "message": "Method not allowed. Use DELETE or POST."

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    address = profile.addresses.filter(pk=address_id).first()

    if not address:

        return _address_not_found_response()



    with transaction.atomic():

        address = UserAddress.objects.select_for_update().get(pk=address.pk, user=profile)

        deleted_id = address.id

        was_default = address.is_default

        address.delete()

        if was_default:

            replacement = profile.addresses.order_by('-created_at').first()

            if replacement:

                replacement.is_default = True

                replacement.save(update_fields=['is_default', 'updated_at'])



    return JsonResponse({

        "success": True,

        "message": "Address deleted successfully",

        "deleted_address_id": deleted_id,

    }, status=200)





@csrf_exempt
def api_user_banners(request):
    """
    API: Fetch promotional banners for mobile app home screen / web carousel
    Endpoints: GET /api/user/banners/ or /api/banners/
    Returns active banners ordered by display_order.
    Response includes:
      - image: string (URL to banner image)
      - title: string (banner headline)
      - category_id: int | null (target category for 'Shop Deals')
      - full details: subtitle, badge_text, button_text, link_url, etc.
    """
    if request.method != 'GET':
        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    banners_qs = Banner.objects.filter(status='ACTIVE').select_related('category').order_by('display_order', '-created_at')
    banners_data = [banner.to_dict(request=request) for banner in banners_qs]

    return JsonResponse({
        "success": True,
        "message": "Banners fetched successfully",
        "count": len(banners_data),
        "banners": banners_data,
    }, status=200)


@csrf_exempt

def api_user_category_list(request):

    """

    API: List all active categories for customer shopping

    Endpoint: GET /api/user/categories/ (alias /api/user/category/list/)

    """

    if request.method != 'GET':

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    qs = Category.objects.filter(status='ACTIVE')

    q = request.GET.get('q', '').strip()

    if q:

        qs = qs.filter(name__icontains=q)



    categories_data = [cat.to_dict() for cat in qs]



    return JsonResponse({

        "success": True,

        "message": "Categories fetched successfully",

        "count": len(categories_data),

        "categories": categories_data,

    }, status=200)





@csrf_exempt

def api_user_category_detail(request, category_id):

    """

    API: Get details for a specific active category

    Endpoint: GET /api/user/categories/<category_id>/ (alias /api/user/category/detail/<category_id>/)

    """

    if request.method != 'GET':

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    category = Category.objects.filter(id=category_id, status='ACTIVE').first()

    if not category:

        return JsonResponse({

            "success": False,

            "message": f"Category with ID '{category_id}' was not found or is inactive."

        }, status=404)



    return JsonResponse({

        "success": True,

        "message": "Category fetched successfully",

        "category": category.to_dict(),

    }, status=200)





@csrf_exempt

def api_user_category_products(request, category_id):

    """

    API: Fetch active approved products under a specific category with filtering, sorting & pagination

    Endpoint: GET /api/user/categories/<category_id>/products/ (alias /api/user/category/products/<category_id>/)

    """

    if request.method != 'GET':

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    category = Category.objects.filter(id=category_id, status='ACTIVE').first()

    if not category:

        return JsonResponse({

            "success": False,

            "message": f"Category with ID '{category_id}' was not found or is inactive."

        }, status=404)



    products_qs = Product.objects.select_related('vendor', 'category').filter(

        category=category,

        status='ACTIVE',

        is_approved=True,

        vendor__status='APPROVED',

    ).annotate(

        effective_price=Coalesce(

            Min(

                Coalesce(

                    'variants__discount_price',

                    'variants__price',

                    'discount_price',

                    'price',

                    output_field=DecimalField(max_digits=10, decimal_places=2),

                ),

                filter=Q(variants__is_active=True),

            ),

            Coalesce(

                'discount_price',

                'price',

                output_field=DecimalField(max_digits=10, decimal_places=2),

            ),

            output_field=DecimalField(max_digits=10, decimal_places=2),

        )

    )



    # Search keyword filter within category

    q = request.GET.get('q', '').strip()

    if q:

        for term in q.split():

            products_qs = products_qs.filter(

                Q(name__icontains=term) |

                Q(description__icontains=term) |

                Q(sku__icontains=term) |

                Q(vendor__business_name__icontains=term)

            )



    commission_rate = CommissionSetting.current_rate()

    price_multiplier = (Decimal('100') + commission_rate) / Decimal('100')

    # Price range filters use the final customer price (vendor price + commission).

    min_price_raw = request.GET.get('min_price')

    if min_price_raw not in [None, '']:

        try:

            min_price = Decimal(min_price_raw)

            if not min_price.is_finite():

                raise ValueError

            if min_price < 0:

                return JsonResponse({"success": False, "message": "Query parameter 'min_price' cannot be negative."}, status=400)

            products_qs = products_qs.filter(effective_price__gte=min_price / price_multiplier)

        except (InvalidOperation, ValueError, TypeError):

            return JsonResponse({"success": False, "message": "Query parameter 'min_price' must be a valid number."}, status=400)



    max_price_raw = request.GET.get('max_price')

    if max_price_raw not in [None, '']:

        try:

            max_price = Decimal(max_price_raw)

            if not max_price.is_finite():

                raise ValueError

            if max_price < 0:

                return JsonResponse({"success": False, "message": "Query parameter 'max_price' cannot be negative."}, status=400)

            products_qs = products_qs.filter(effective_price__lte=max_price / price_multiplier)

        except (InvalidOperation, ValueError, TypeError):

            return JsonResponse({"success": False, "message": "Query parameter 'max_price' must be a valid number."}, status=400)



    # In-stock filter

    in_stock_raw = request.GET.get('in_stock', '').strip().lower()

    if in_stock_raw in ['true', '1', 'yes']:

        products_qs = products_qs.filter(stock_quantity__gt=0)



    # Sorting

    sort = request.GET.get('sort', 'newest').strip() or 'newest'

    sort_options = {

        'price_low_to_high': ('effective_price', 'id'),

        'price_high_to_low': ('-effective_price', '-id'),

        'newest': ('-created_at', '-id'),

    }

    if sort not in sort_options:

        return JsonResponse({

            "success": False,

            "message": "Invalid sort option. Use 'price_low_to_high', 'price_high_to_low', or 'newest'."

        }, status=400)



    products_qs = products_qs.order_by(*sort_options[sort])



    # Pagination

    try:

        page = max(1, int(request.GET.get('page', 1)))

    except (ValueError, TypeError):

        return JsonResponse({"success": False, "message": "Query parameter 'page' must be a valid integer."}, status=400)



    try:

        limit = min(100, max(1, int(request.GET.get('limit', 20))))

    except (ValueError, TypeError):

        return JsonResponse({"success": False, "message": "Query parameter 'limit' must be a valid integer."}, status=400)



    total_products = products_qs.count()

    total_pages = (total_products + limit - 1) // limit if total_products > 0 else 1

    offset = (page - 1) * limit

    page_items = products_qs[offset:offset + limit]



    product_list = []

    for product in page_items:

        customer_price = customer_price_for(product.price, commission_rate)

        customer_discount_price = (

            customer_price_for(product.discount_price, commission_rate)

            if product.discount_price is not None else None

        )

        customer_effective_price = customer_price_for(product.effective_price, commission_rate)

        product_list.append({

            "id": product.id,

            "name": product.name,

            "sku": product.sku,

            "price": float(customer_price),

            "discount_price": float(customer_discount_price) if customer_discount_price is not None else None,

            "effective_price": float(customer_effective_price),

            "commission_rate_percent": float(commission_rate),

            "commission_amount": float(commission_amount_for(product.effective_price, commission_rate)),

            "image_url": product.image_url,

            "category_id": category.id,

            "category_name": category.name,

            "vendor_name": product.vendor.business_name if product.vendor else None,

            "stock_quantity": product.stock_quantity,

            "in_stock": product.stock_quantity > 0,

            "has_variants": product.has_variants,

            "variant_count": product.active_variant_count,

        })



    return JsonResponse({

        "success": True,

        "category": {

            "id": category.id,

            "name": category.name,

            "description": category.description,

            "image_url": category.image_url,

            "total_products": category.products_count,

        },

        "total_products": total_products,

        "page": page,

        "total_pages": total_pages,

        "has_next": page < total_pages,

        "products": product_list,

    }, status=200)





def api_product_search(request):

    """Public customer catalog search with filtering, sorting, and pagination."""

    if request.method != 'GET':

        return JsonResponse({

            "success": False,

            "message": "Method not allowed. Use GET."

        }, status=405)



    raw_query = request.GET.get('q')

    query = raw_query.strip() if raw_query is not None else ''

    if raw_query is not None and not query:

        return JsonResponse({

            "success": False,

            "message": "Search parameter 'q' cannot be empty."

        }, status=400)



    def parse_positive_integer(name, default, maximum=None):

        raw_value = request.GET.get(name)

        if raw_value in [None, '']:

            return default, None

        try:

            value = int(raw_value)

        except (TypeError, ValueError):

            return None, f"Query parameter '{name}' must be a valid integer."

        if value < 1:

            return None, f"Query parameter '{name}' must be at least 1."

        if maximum is not None and value > maximum:

            return None, f"Query parameter '{name}' cannot exceed {maximum}."

        return value, None



    def parse_price(name):

        raw_value = request.GET.get(name)

        if raw_value in [None, '']:

            return None, None

        try:

            value = Decimal(raw_value)

        except (InvalidOperation, TypeError, ValueError):

            return None, f"Query parameter '{name}' must be a valid number."

        if not value.is_finite():

            return None, f"Query parameter '{name}' must be a finite number."

        if value < 0:

            return None, f"Query parameter '{name}' cannot be negative."

        return value, None



    page, error = parse_positive_integer('page', 1)

    if error:

        return JsonResponse({"success": False, "message": error}, status=400)



    limit, error = parse_positive_integer('limit', 20, maximum=100)

    if error:

        return JsonResponse({"success": False, "message": error}, status=400)



    category_id = None

    raw_category_id = request.GET.get('category_id')

    if raw_category_id not in [None, '']:

        try:

            category_id = int(raw_category_id)

        except (TypeError, ValueError):

            return JsonResponse({

                "success": False,

                "message": "Query parameter 'category_id' must be a valid integer."

            }, status=400)

        if category_id < 1:

            return JsonResponse({

                "success": False,

                "message": "Query parameter 'category_id' must be at least 1."

            }, status=400)

        if not Category.objects.filter(pk=category_id).exists():

            return JsonResponse({

                "success": False,

                "message": f"Category with ID '{category_id}' was not found."

            }, status=404)



    min_price, error = parse_price('min_price')

    if error:

        return JsonResponse({"success": False, "message": error}, status=400)

    max_price, error = parse_price('max_price')

    if error:

        return JsonResponse({"success": False, "message": error}, status=400)

    if min_price is not None and max_price is not None and min_price > max_price:

        return JsonResponse({

            "success": False,

            "message": "Query parameter 'min_price' cannot be greater than 'max_price'."

        }, status=400)

    commission_rate = CommissionSetting.current_rate()

    price_multiplier = (Decimal('100') + commission_rate) / Decimal('100')



    raw_in_stock = request.GET.get('in_stock')

    in_stock_only = False

    if raw_in_stock not in [None, '']:

        normalized_in_stock = raw_in_stock.strip().lower()

        if normalized_in_stock in ['true', '1']:

            in_stock_only = True

        elif normalized_in_stock not in ['false', '0']:

            return JsonResponse({

                "success": False,

                "message": "Query parameter 'in_stock' must be true, false, 1, or 0."

            }, status=400)



    sort = request.GET.get('sort', 'newest').strip() or 'newest'

    sort_options = {

        'price_low_to_high': ('effective_price', 'id'),

        'price_high_to_low': ('-effective_price', '-id'),

        'newest': ('-created_at', '-id'),

    }

    if sort not in sort_options:

        return JsonResponse({

            "success": False,

            "message": (

                "Invalid sort option. Use 'price_low_to_high', "

                "'price_high_to_low', or 'newest'."

            )

        }, status=400)



    products = Product.objects.select_related('vendor', 'category').filter(

        status__in=['ACTIVE', 'OUT_OF_STOCK'],

        is_approved=True,

        vendor__status='APPROVED',

    ).filter(

        Q(category__isnull=True) | Q(category__status='ACTIVE')

    ).annotate(

        effective_price=Coalesce(

            Min(

                Coalesce(

                    'variants__discount_price',

                    'variants__price',

                    'discount_price',

                    'price',

                    output_field=DecimalField(max_digits=10, decimal_places=2),

                ),

                filter=Q(variants__is_active=True),

            ),

            Coalesce(

                'discount_price',

                'price',

                output_field=DecimalField(max_digits=10, decimal_places=2),

            ),

            output_field=DecimalField(max_digits=10, decimal_places=2),

        )

    )



    if query:

        for term in query.split():

            products = products.filter(

                Q(name__icontains=term) |

                Q(description__icontains=term) |

                Q(sku__icontains=term) |

                Q(category__name__icontains=term) |

                Q(vendor__business_name__icontains=term)

            )



    if category_id is not None:

        products = products.filter(category_id=category_id)

    if min_price is not None:

        products = products.filter(effective_price__gte=min_price / price_multiplier)

    if max_price is not None:

        products = products.filter(effective_price__lte=max_price / price_multiplier)

    if in_stock_only:

        products = products.filter(stock_quantity__gt=0)



    products = products.order_by(*sort_options[sort])

    total_matches = products.count()

    total_pages = (total_matches + limit - 1) // limit

    offset = (page - 1) * limit

    page_products = products[offset:offset + limit]



    product_data = [{

        'id': product.id,

        'name': product.name,

        'sku': product.sku,

        'price': float(customer_price_for(product.price, commission_rate)),

        'discount_price': (

            float(customer_price_for(product.discount_price, commission_rate))

            if product.discount_price is not None else None

        ),

        'effective_price': float(customer_price_for(product.effective_price, commission_rate)),

        'commission_rate_percent': float(commission_rate),

        'commission_amount': float(commission_amount_for(product.effective_price, commission_rate)),

        'image_url': product.image_url,

        'category_id': product.category_id,

        'category_name': product.category.name if product.category else None,

        'vendor_name': product.vendor.business_name,

        'stock_quantity': product.stock_quantity,

        'in_stock': product.stock_quantity > 0,

        'has_variants': product.has_variants,

        'variant_count': product.active_variant_count,

    } for product in page_products]



    return JsonResponse({

        "success": True,

        "query": query,

        "total_matches": total_matches,

        "page": page,

        "total_pages": total_pages,

        "has_next": page < total_pages,

        "products": product_data,

    }, status=200)


def api_random_products(request):

    """Public, non-cached product discovery feed with a fresh random order per request."""

    if request.method != 'GET':

        return JsonResponse({

            "success": False,

            "message": "Method not allowed. Use GET."

        }, status=405)



    raw_limit = request.GET.get('limit', '20').strip()

    try:

        limit = int(raw_limit)

    except (TypeError, ValueError):

        return JsonResponse({

            "success": False,

            "message": "Query parameter 'limit' must be a valid integer."

        }, status=400)

    if limit < 1 or limit > 100:

        return JsonResponse({

            "success": False,

            "message": "Query parameter 'limit' must be between 1 and 100."

        }, status=400)



    products = Product.objects.select_related('vendor', 'category').filter(

        status='ACTIVE',

        is_approved=True,

        vendor__status='APPROVED',

        stock_quantity__gt=0,

    ).filter(

        Q(category__isnull=True) | Q(category__status='ACTIVE')

    ).annotate(

        effective_price=Coalesce(

            Min(

                Coalesce(

                    'variants__discount_price',

                    'variants__price',

                    'discount_price',

                    'price',

                    output_field=DecimalField(max_digits=10, decimal_places=2),

                ),

                filter=Q(variants__is_active=True),

            ),

            Coalesce(

                'discount_price',

                'price',

                output_field=DecimalField(max_digits=10, decimal_places=2),

            ),

            output_field=DecimalField(max_digits=10, decimal_places=2),

        )

    )



    raw_category_id = request.GET.get('category_id', '').strip()

    if raw_category_id:

        try:

            category_id = int(raw_category_id)

            if category_id < 1:

                raise ValueError

        except (TypeError, ValueError):

            return JsonResponse({

                "success": False,

                "message": "Query parameter 'category_id' must be a valid positive integer."

            }, status=400)

        category = Category.objects.filter(pk=category_id, status='ACTIVE').first()

        if not category:

            return JsonResponse({

                "success": False,

                "message": f"Active category with ID '{category_id}' was not found."

            }, status=404)

        products = products.filter(category_id=category_id)



    total_available = products.count()

    random_products = list(products.order_by('?')[:limit])

    commission_rate = CommissionSetting.current_rate()

    product_data = [{

        'id': product.id,

        'name': product.name,

        'sku': product.sku,

        'price': float(customer_price_for(product.price, commission_rate)),

        'discount_price': (

            float(customer_price_for(product.discount_price, commission_rate))

            if product.discount_price is not None else None

        ),

        'effective_price': float(customer_price_for(product.effective_price, commission_rate)),

        'commission_rate_percent': float(commission_rate),

        'commission_amount': float(commission_amount_for(product.effective_price, commission_rate)),

        'image_url': product.image_url,

        'category_id': product.category_id,

        'category_name': product.category.name if product.category else None,

        'vendor_id': product.vendor_id,

        'vendor_name': product.vendor.business_name,

        'stock_quantity': product.stock_quantity,

        'in_stock': True,

        'has_variants': product.has_variants,

        'variant_count': product.active_variant_count,

    } for product in random_products]



    response = JsonResponse({

        "success": True,

        "message": "Random products fetched successfully",

        "randomized": True,

        "total_available": total_available,

        "returned_count": len(product_data),

        "products": product_data,

    }, status=200)

    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'

    response['Pragma'] = 'no-cache'

    response['Expires'] = '0'

    return response





@csrf_exempt

def api_user_product_detail(request, product_id):

    """

    API: Fetch complete single product details for mobile app and customer storefront.

    Endpoint: GET /api/user/products/<product_id>/ (alias /api/user/product/detail/<product_id>/)

    """

    if request.method != 'GET':

        return JsonResponse({

            "success": False,

            "message": "Method not allowed. Use GET."

        }, status=405)



    product = Product.objects.select_related('vendor', 'category').prefetch_related('variants').filter(

        id=product_id,

        status__in=['ACTIVE', 'OUT_OF_STOCK'],

        is_approved=True,

        vendor__status='APPROVED',

    ).filter(

        Q(category__isnull=True) | Q(category__status='ACTIVE')

    ).first()



    if not product:

        return JsonResponse({

            "success": False,

            "message": f"Product with ID '{product_id}' was not found or is unavailable."

        }, status=404)



    commission_rate = CommissionSetting.current_rate()

    price = float(customer_price_for(product.price, commission_rate))

    discount_price = (

        float(customer_price_for(product.discount_price, commission_rate))

        if product.discount_price is not None else None

    )

    base_effective_price = product.customer_effective_price

    effective_price = float(customer_price_for(base_effective_price, commission_rate))

    savings_amount = round(price - effective_price, 2) if effective_price < price else 0.0

    savings_percentage = round(((price - effective_price) / price) * 100, 1) if effective_price < price and price > 0 else 0.0



    in_stock = product.stock_quantity > 0

    low_stock_warning = in_stock and (product.stock_quantity <= product.low_stock_threshold)



    category_data = None

    if product.category:

        category_data = {

            "id": product.category.id,

            "name": product.category.name,

            "description": product.category.description,

            "image_url": product.category.image_url,

        }



    vendor_data = {

        "id": product.vendor.id,

        "vendor_code": product.vendor.vendor_code,

        "business_name": product.vendor.business_name,

        "owner_name": product.vendor.owner_name,

        "city": product.vendor.city,

        "state": product.vendor.state,

        "store_logo": product.vendor.logo_url,

    }



    variants = [

        _customer_variant_dict(v, commission_rate)

        for v in product.variants.filter(is_active=True).order_by('id')

    ]

    has_variants = len(variants) > 0

    available_colors = sorted({v['color'] for v in variants if v.get('color')})

    available_sizes = sorted({v['size'] for v in variants if v.get('size')})

    available_materials = sorted({v['material'] for v in variants if v.get('material')})



    # Related items in same category (or same vendor if uncategorized)

    related_qs = Product.objects.select_related('vendor', 'category').filter(

        status__in=['ACTIVE', 'OUT_OF_STOCK'],

        is_approved=True,

        vendor__status='APPROVED',

    ).filter(

        Q(category__isnull=True) | Q(category__status='ACTIVE')

    ).exclude(id=product.id)



    if product.category:

        related_qs = related_qs.filter(category=product.category)

    else:

        related_qs = related_qs.filter(vendor=product.vendor)



    related_products = []

    for rel in related_qs.order_by('-created_at')[:6]:

        rel_price = float(customer_price_for(rel.price, commission_rate))

        rel_discount = (

            float(customer_price_for(rel.discount_price, commission_rate))

            if rel.discount_price is not None else None

        )

        related_products.append({

            "id": rel.id,

            "name": rel.name,

            "sku": rel.sku,

            "price": rel_price,

            "discount_price": rel_discount,

            "effective_price": float(customer_price_for(rel.customer_effective_price, commission_rate)),

            "commission_rate_percent": float(commission_rate),

            "commission_amount": float(commission_amount_for(rel.customer_effective_price, commission_rate)),

            "image_url": rel.image_url,

            "category_id": rel.category_id,

            "category_name": rel.category.name if rel.category else None,

            "vendor_name": rel.vendor.business_name if rel.vendor else None,

            "stock_quantity": rel.stock_quantity,

            "in_stock": rel.stock_quantity > 0,

            "has_variants": rel.has_variants,

            "variant_count": rel.active_variant_count,

        })



    product_data = {

        "id": product.id,

        "name": product.name,

        "sku": product.sku,

        "description": product.description,

        "price": price,

        "discount_price": discount_price,

        "effective_price": effective_price,

        "commission_rate_percent": float(commission_rate),

        "commission_amount": float(commission_amount_for(base_effective_price, commission_rate)),

        "savings_amount": savings_amount,

        "savings_percentage": savings_percentage,

        "stock_quantity": product.stock_quantity,

        "low_stock_threshold": product.low_stock_threshold,

        "unit": product.unit,

        "image_url": product.image_url,

        "status": product.status,

        "in_stock": in_stock,

        "low_stock_warning": low_stock_warning,

        "is_approved": product.is_approved,

        "category": category_data,

        "vendor": vendor_data,

        "has_variants": has_variants,

        "total_variants": len(variants),

        "available_colors": available_colors,

        "available_sizes": available_sizes,

        "available_materials": available_materials,

        "variants": variants,

        "created_at": product.created_at.isoformat() if product.created_at else None,

        "updated_at": product.updated_at.isoformat() if product.updated_at else None,

    }



    return JsonResponse({

        "success": True,

        "message": "Product details fetched successfully",

        "product": product_data,

        "related_products": related_products,

    }, status=200)





@csrf_exempt

def api_user_product_variants(request, product_id):

    """Return active variants and option summaries for one customer-visible product."""

    if request.method != 'GET':

        return JsonResponse({

            "success": False,

            "message": "Method not allowed. Use GET."

        }, status=405)



    product = Product.objects.select_related('vendor', 'category').filter(

        id=product_id,

        status__in=['ACTIVE', 'OUT_OF_STOCK'],

        is_approved=True,

        vendor__status='APPROVED',

    ).filter(

        Q(category__isnull=True) | Q(category__status='ACTIVE')

    ).first()

    if not product:

        return JsonResponse({

            "success": False,

            "message": f"Product with ID '{product_id}' was not found or is unavailable."

        }, status=404)



    variants = list(product.variants.filter(is_active=True).order_by('id'))

    commission_rate = CommissionSetting.current_rate()

    available_colors = sorted({variant.color for variant in variants if variant.color})

    available_sizes = sorted({variant.size for variant in variants if variant.size})

    available_materials = sorted({variant.material for variant in variants if variant.material})



    return JsonResponse({

        "success": True,

        "product_id": product.id,

        "product_name": product.name,

        "total_variants": len(variants),

        "available_colors": available_colors,

        "available_sizes": available_sizes,

        "available_materials": available_materials,

        "commission_rate_percent": float(commission_rate),

        "variants": [_customer_variant_dict(variant, commission_rate) for variant in variants],

    }, status=200)





@csrf_exempt

def api_user_variant_detail(request, variant_id):

    """Return one active variant belonging to a customer-visible product."""

    if request.method != 'GET':

        return JsonResponse({

            "success": False,

            "message": "Method not allowed. Use GET."

        }, status=405)



    variant = ProductVariant.objects.select_related('product', 'product__vendor', 'product__category').filter(

        id=variant_id,

        is_active=True,

        product__status__in=['ACTIVE', 'OUT_OF_STOCK'],

        product__is_approved=True,

        product__vendor__status='APPROVED',

    ).filter(

        Q(product__category__isnull=True) | Q(product__category__status='ACTIVE')

    ).first()

    if not variant:

        return JsonResponse({

            "success": False,

            "message": f"Variant with ID '{variant_id}' was not found or is unavailable."

        }, status=404)



    commission_rate = CommissionSetting.current_rate()

    return JsonResponse({

        "success": True,

        "variant": _customer_variant_dict(variant, commission_rate),

    }, status=200)





def _is_customer_product_available(product):

    """Apply the shared customer-facing product availability rules."""

    return (

        product.status == 'ACTIVE'

        and product.is_approved

        and product.vendor.status == 'APPROVED'

        and (product.category is None or product.category.status == 'ACTIVE')

    )





def _customer_cart_payload(profile):

    """Serialize a customer's cart with totals calculated from current prices."""

    cart_items = list(

        CartItem.objects.filter(user=profile)

        .select_related('product', 'product__vendor', 'product__category', 'variant')

        .order_by('-updated_at', '-id')

    )

    regular_subtotal = sum(

        (item.regular_unit_price * item.quantity for item in cart_items),

        Decimal('0.00'),

    )

    total = sum((item.line_total for item in cart_items), Decimal('0.00'))

    return {

        'item_count': len(cart_items),

        'total_quantity': sum(item.quantity for item in cart_items),

        'regular_subtotal': float(regular_subtotal),

        'discount': float(regular_subtotal - total),

        'total': float(total),

        'items': [item.to_dict() for item in cart_items],

    }





@csrf_exempt

def api_user_cart_add(request):

    """

    Add a purchasable product or variant to the authenticated customer's cart.



    Endpoint: POST /api/user/cart/add/

    Body: {"product_id": 50, "variant_id": 1, "quantity": 2}

    """

    if request.method != 'POST':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use POST.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    data = _parse_request_data(request)

    try:

        product_id = int(data.get('product_id', ''))

        if product_id <= 0:

            raise ValueError

    except (TypeError, ValueError):

        return JsonResponse({

            'success': False,

            'message': 'product_id must be a valid positive integer.',

        }, status=400)



    try:

        quantity = int(data.get('quantity', 1))

        if quantity <= 0:

            raise ValueError

    except (TypeError, ValueError):

        return JsonResponse({

            'success': False,

            'message': 'quantity must be a valid positive integer.',

        }, status=400)



    raw_variant_id = data.get('variant_id')

    variant_id = None

    if raw_variant_id not in (None, ''):

        try:

            variant_id = int(raw_variant_id)

            if variant_id <= 0:

                raise ValueError

        except (TypeError, ValueError):

            return JsonResponse({

                'success': False,

                'message': 'variant_id must be a valid positive integer.',

            }, status=400)



    with transaction.atomic():

        product = (

            Product.objects.select_for_update()

            .select_related('vendor', 'category')

            .filter(pk=product_id)

            .first()

        )

        if not product:

            return JsonResponse({

                'success': False,

                'message': f"Product with ID '{product_id}' was not found.",

            }, status=404)



        if not _is_customer_product_available(product):

            return JsonResponse({

                'success': False,

                'message': 'This product is currently unavailable for purchase.',

            }, status=400)



        has_variants = ProductVariant.objects.filter(product=product).exists()

        variant = None

        if has_variants:

            if variant_id is None:

                return JsonResponse({

                    'success': False,

                    'message': 'variant_id is required for this product. Please select a product variant.',

                }, status=400)

            variant = (

                ProductVariant.objects.select_for_update()

                .filter(pk=variant_id, product=product, is_active=True)

                .first()

            )

            if not variant:

                return JsonResponse({

                    'success': False,

                    'message': f"Active variant with ID '{variant_id}' was not found for this product.",

                }, status=404)

        elif variant_id is not None:

            return JsonResponse({

                'success': False,

                'message': 'This product does not have variants. Remove variant_id and try again.',

            }, status=400)



        available_stock = variant.stock_quantity if variant else product.stock_quantity

        existing_item = (

            CartItem.objects.select_for_update()

            .filter(user=profile, product=product, variant=variant)

            .first()

        )

        existing_quantity = existing_item.quantity if existing_item else 0

        requested_total = existing_quantity + quantity



        if available_stock <= 0:

            return JsonResponse({

                'success': False,

                'message': 'This item is out of stock.',

                'available_stock': 0,

            }, status=400)

        if requested_total > available_stock:

            return JsonResponse({

                'success': False,

                'message': f'Only {available_stock} item(s) are currently available.',

                'available_stock': available_stock,

                'quantity_already_in_cart': existing_quantity,

                'requested_additional_quantity': quantity,

            }, status=400)



        if existing_item:

            existing_item.quantity = requested_total

            existing_item.save(update_fields=['quantity', 'updated_at'])

            cart_item = existing_item

            message = 'Cart quantity updated successfully.'

            response_status = 200

        else:

            cart_item = CartItem.objects.create(

                user=profile,

                product=product,

                variant=variant,

                quantity=quantity,

            )

            message = 'Product added to cart successfully.'

            response_status = 201



        cart_item = CartItem.objects.select_related('product', 'variant').get(pk=cart_item.pk)

        cart = _customer_cart_payload(profile)



    return JsonResponse({

        'success': True,

        'message': message,

        'cart_item': cart_item.to_dict(),

        'cart': cart,

    }, status=response_status)





@csrf_exempt

def api_user_cart_list(request):

    """

    Get all items in the customer's cart with subtotal, discount, and total.



    Endpoint: GET /api/user/cart/

    Headers: Authorization: Bearer <customer_token>

    """

    if request.method != 'GET':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use GET.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    cart = _customer_cart_payload(profile)

    return JsonResponse({

        'success': True,

        'cart': cart,

    }, status=200)





@csrf_exempt

def api_user_cart_remove(request):

    """

    Remove an item from the customer's cart.



    Endpoint: POST /api/user/cart/remove/

    Headers: Authorization: Bearer <customer_token>

    Body: {"cart_item_id": 1} OR {"product_id": 81, "variant_id": 16}

    """

    if request.method not in ['POST', 'DELETE']:

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use POST or DELETE.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    data = _parse_request_data(request)

    cart_item_id = data.get('cart_item_id')

    product_id = data.get('product_id')

    variant_id = data.get('variant_id')



    qs = CartItem.objects.filter(user=profile)

    if cart_item_id:

        try:

            cart_item_id = int(cart_item_id)

            qs = qs.filter(id=cart_item_id)

        except (ValueError, TypeError):

            return JsonResponse({'success': False, 'message': 'cart_item_id must be a valid integer.'}, status=400)

    elif product_id:

        try:

            product_id = int(product_id)

            qs = qs.filter(product_id=product_id)

            if variant_id:

                qs = qs.filter(variant_id=int(variant_id))

        except (ValueError, TypeError):

            return JsonResponse({'success': False, 'message': 'product_id and variant_id must be valid integers.'}, status=400)

    else:

        return JsonResponse({

            'success': False,

            'message': 'cart_item_id or product_id is required.',

        }, status=400)



    deleted_count, _ = qs.delete()

    if deleted_count == 0:

        return JsonResponse({

            'success': False,

            'message': 'Cart item not found.',

        }, status=404)



    cart = _customer_cart_payload(profile)

    return JsonResponse({

        'success': True,

        'message': 'Item removed from cart successfully.',

        'cart': cart,

    }, status=200)





@csrf_exempt

def api_user_cart_clear(request):

    """

    Clear all items from the customer's cart.



    Endpoint: POST /api/user/cart/clear/

    Headers: Authorization: Bearer <customer_token>

    """

    if request.method not in ['POST', 'DELETE']:

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use POST or DELETE.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    CartItem.objects.filter(user=profile).delete()

    cart = _customer_cart_payload(profile)

    return JsonResponse({

        'success': True,

        'message': 'Cart cleared successfully.',

        'cart': cart,

    }, status=200)





@csrf_exempt

def api_user_checkout(request):

    """

    Convert the authenticated customer's cart into an order.



    Endpoint: POST /api/user/checkout/

    Body: {"address_id": 1, "payment_method": "COD"}

          {"address_id": 1, "payment_method": "ONLINE"}

    """

    if request.method != 'POST':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use POST.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    data = _parse_request_data(request)

    try:

        address_id = int(data.get('address_id', ''))

        if address_id <= 0:

            raise ValueError

    except (TypeError, ValueError):

        return JsonResponse({

            'success': False,

            'message': 'address_id must be a valid positive integer.',

        }, status=400)



    raw_payment_method = str(data.get('payment_method', '')).strip().upper().replace(' ', '_')

    payment_aliases = {

        'COD': 'COD',

        'CASH_ON_DELIVERY': 'COD',

        'ONLINE': 'ONLINE',

        'ONLINE_PAYMENT': 'ONLINE',

        'PREPAID': 'ONLINE',

    }

    payment_method = payment_aliases.get(raw_payment_method)

    if not payment_method:

        return JsonResponse({

            'success': False,

            'message': "payment_method must be either 'COD' or 'ONLINE'.",

        }, status=400)



    with transaction.atomic():

        address = UserAddress.objects.select_for_update().filter(

            pk=address_id,

            user=profile,

        ).first()

        if not address:

            return JsonResponse({

                'success': False,

                'message': f"Address with ID '{address_id}' was not found for this customer.",

            }, status=404)



        cart_items = list(

            CartItem.objects.select_for_update()

            .filter(user=profile)

            .order_by('id')

        )

        if not cart_items:

            return JsonResponse({

                'success': False,

                'message': 'Your cart is empty. Add at least one item before checkout.',

            }, status=400)



        product_ids = {item.product_id for item in cart_items}

        variant_ids = {item.variant_id for item in cart_items if item.variant_id}

        products = {

            product.id: product

            for product in Product.objects.select_for_update()

            .select_related('vendor', 'category')

            .filter(id__in=product_ids)

        }

        variants = {

            variant.id: variant

            for variant in ProductVariant.objects.select_for_update()

            .select_related('product')

            .filter(id__in=variant_ids)

        }



        checkout_lines = []

        total_amount = Decimal('0.00')

        commission_rate = CommissionSetting.current_rate()

        for cart_item in cart_items:

            product = products.get(cart_item.product_id)

            if not product or not _is_customer_product_available(product):

                return JsonResponse({

                    'success': False,

                    'message': f"'{getattr(product, 'name', 'A cart product')}' is no longer available.",

                    'cart_item_id': cart_item.id,

                }, status=400)



            product_has_variants = ProductVariant.objects.filter(product=product).exists()

            variant = variants.get(cart_item.variant_id) if cart_item.variant_id else None

            if product_has_variants and not variant:

                return JsonResponse({

                    'success': False,

                    'message': f"Please select an active variant for '{product.name}'.",

                    'cart_item_id': cart_item.id,

                }, status=400)

            if variant and (variant.product_id != product.id or not variant.is_active):

                return JsonResponse({

                    'success': False,

                    'message': f"The selected variant for '{product.name}' is no longer available.",

                    'cart_item_id': cart_item.id,

                }, status=400)



            stock_target = variant or product

            if cart_item.quantity > stock_target.stock_quantity:

                return JsonResponse({

                    'success': False,

                    'message': f"Only {stock_target.stock_quantity} item(s) of '{product.name}' are available.",

                    'cart_item_id': cart_item.id,

                    'available_stock': stock_target.stock_quantity,

                    'requested_quantity': cart_item.quantity,

                }, status=400)



            if variant and variant.discount_price is not None:

                vendor_unit_price = variant.discount_price

            elif variant and variant.price is not None:

                vendor_unit_price = variant.price

            elif product.discount_price is not None:

                vendor_unit_price = product.discount_price

            else:

                vendor_unit_price = product.price



            unit_commission = commission_amount_for(vendor_unit_price, commission_rate)

            unit_price = customer_price_for(vendor_unit_price, commission_rate)

            line_total = unit_price * cart_item.quantity

            vendor_line_total = vendor_unit_price * cart_item.quantity

            line_commission = unit_commission * cart_item.quantity

            total_amount += line_total

            checkout_lines.append({

                'cart_item': cart_item,

                'product': product,

                'variant': variant,

                'stock_target': stock_target,

                'unit_price': unit_price,

                'vendor_unit_price': vendor_unit_price,

                'commission_rate': commission_rate,

                'commission_amount': line_commission,

                'vendor_line_total': vendor_line_total,

                'line_total': line_total,

            })



        address_parts = [

            address.address_line_1,

            address.address_line_2,

            address.landmark,

            address.country,

        ]

        shipping_address = ', '.join(part for part in address_parts if part)

        order = Order.objects.create(

            customer=profile,

            customer_name=address.full_name or profile.full_name,

            customer_phone=address.phone or profile.phone,

            customer_email=profile.email or '',

            shipping_address=shipping_address,

            shipping_city=address.city,

            shipping_state=address.state,

            shipping_pincode=address.pincode,

            total_amount=total_amount,

            payment_method=payment_method,

            payment_status='PENDING',

            status='PENDING',

        )



        provider_name = str(data.get('provider', '')).strip()

        if not provider_name:

            provider_name = '' if payment_method == 'ONLINE' else 'COD'



        payment = PaymentTransaction.objects.create(

            order=order,

            customer=profile,

            method=payment_method,

            amount=total_amount,

            currency='INR',

            status='INITIATED' if payment_method == 'ONLINE' else 'PENDING',

            provider=provider_name,

        )



        for line in checkout_lines:

            product = line['product']

            variant = line['variant']

            cart_item = line['cart_item']

            stock_target = line['stock_target']

            previous_stock = stock_target.stock_quantity

            new_stock = previous_stock - cart_item.quantity



            order_item = OrderItem.objects.create(

                order=order,

                vendor=product.vendor,

                product=product,

                variant=variant,

                product_name=product.name,

                product_sku=variant.sku if variant else product.sku,

                variant_title=variant.title if variant else '',

                price=line['unit_price'],

                vendor_unit_price=line['vendor_unit_price'],

                commission_rate=line['commission_rate'],

                commission_amount=line['commission_amount'],

                quantity=cart_item.quantity,

                total_price=line['line_total'],

                status='PENDING',

            )



            stock_target.stock_quantity = new_stock

            stock_target.save()

            product.refresh_from_db()



            StockLog.objects.create(

                product=product,

                variant=variant,

                vendor=product.vendor,

                movement_type='SALE',

                quantity_changed=-cart_item.quantity,

                previous_stock=previous_stock,

                new_stock=new_stock,

                reason=f"Checkout created order {order.order_number}",

                reference_id=order.order_number,

            )

            OrderStatusHistory.objects.create(

                order=order,

                order_item=order_item,

                vendor=product.vendor,

                old_status='',

                new_status='PENDING',

                notes='Order item created from customer checkout.',

            )



        CartItem.objects.filter(id__in=[item.id for item in cart_items]).delete()



        Notification.objects.create(

            user=profile,

            notification_type='ORDER',

            title='Order placed successfully',

            message=(

                f'Your order {order.order_number} has been placed. Pay cash when it is delivered.'

                if payment_method == 'COD'

                else f'Your order {order.order_number} has been created. Complete the online payment to continue.'

            ),

            order=order,

            data={

                'order_number': order.order_number,

                'payment_method': payment_method,

                'payment_reference': payment.reference,

                'total_amount': float(total_amount),

            },

        )



        order = Order.objects.prefetch_related('items').get(pk=order.pk)

        order_data = order.to_dict()

        payment_data = payment.to_dict()



    if payment_method == 'COD':

        message = 'Order placed successfully. Payment will be collected on delivery.'

    else:

        message = 'Order created successfully. Online payment is required to complete payment.'



    return JsonResponse({

        'success': True,

        'message': message,

        'order': order_data,

        'payment': payment_data,

        'payment_instructions': {

            'action_required': (payment_method == 'ONLINE'),

            'type': payment_method,

            'message': (

                'Please complete online payment with your preferred gateway using the payment reference.'

                if payment_method == 'ONLINE' else

                'Cash on delivery: pay upon parcel arrival.'

            ),

            'verify_url': '/api/user/payment/verify/' if payment_method == 'ONLINE' else None,

        },

        'delivery_address': address.to_dict(),

        'cart_cleared': True,

    }, status=201)





@csrf_exempt

def api_user_payment_verify(request):

    """

    Verify or record payment status for an online order.



    Endpoint: POST /api/user/payment/verify/

    Headers: Authorization: Bearer <customer_token>

    Body:

        {

            "payment_reference": "PAY-20261023-ABCDEF1234",

            "status": "PAID",

            "provider": "RAZORPAY",

            "provider_payment_id": "pay_xyz123",

            "provider_order_id": "order_xyz123"

        }

    """

    if request.method != 'POST':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use POST.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    data = _parse_request_data(request)

    ref = str(data.get('payment_reference', '')).strip()

    order_id = data.get('order_id')

    order_number = str(data.get('order_number', '')).strip()

    raw_status = str(data.get('status', 'PAID')).strip().upper()

    provider = str(data.get('provider', '')).strip() or 'ONLINE'

    provider_payment_id = str(data.get('provider_payment_id', '')).strip()

    provider_order_id = str(data.get('provider_order_id', '')).strip()

    verification_signature = str(

        request.headers.get('X-Payment-Signature', '') or data.get('signature', '')

    ).strip()



    if raw_status not in ['PAID', 'SUCCESS', 'FAILED']:

        return JsonResponse({

            'success': False,

            'message': "status must be 'PAID', 'SUCCESS', or 'FAILED'.",

        }, status=400)



    status_val = 'PAID' if raw_status in ['PAID', 'SUCCESS'] else 'FAILED'



    verification_secret = getattr(settings, 'PAYMENT_WEBHOOK_SECRET', '')

    if verification_secret and verification_signature:

        signed_payload = '|'.join([

            ref,

            raw_status,

            provider,

            provider_order_id,

            provider_payment_id,

        ])

        expected_signature = hmac.new(

            verification_secret.encode('utf-8'),

            signed_payload.encode('utf-8'),

            hashlib.sha256,

        ).hexdigest()

        if not hmac.compare_digest(verification_signature, expected_signature):

            return JsonResponse({

                'success': False,

                'message': 'Payment verification signature is invalid.',

            }, status=403)

    elif verification_secret and not getattr(settings, 'DEBUG', True):

        if not verification_signature:

            return JsonResponse({

                'success': False,

                'message': 'X-Payment-Signature header is required for payment verification.',

            }, status=403)



    payment = None

    if ref:

        payment = PaymentTransaction.objects.filter(reference=ref, customer=profile).select_related('order').first()

    elif order_id:

        payment = PaymentTransaction.objects.filter(order_id=order_id, customer=profile).select_related('order').first()

    elif order_number:

        payment = PaymentTransaction.objects.filter(order__order_number=order_number, customer=profile).select_related('order').first()



    if not payment:

        return JsonResponse({

            'success': False,

            'message': 'Payment transaction not found for this customer.',

        }, status=404)



    order = payment.order

    previous_payment_status = payment.status

    with transaction.atomic():

        payment.status = status_val

        payment.provider = provider

        if provider_payment_id:

            payment.provider_payment_id = provider_payment_id

        if provider_order_id:

            payment.provider_order_id = provider_order_id



        if status_val == 'PAID':

            payment.paid_at = timezone.now()

            order.payment_status = 'PAID'

            order.save(update_fields=['payment_status', 'updated_at'])

            OrderStatusHistory.objects.create(

                order=order,

                old_status=order.status,

                new_status=order.status,

                notes=f"Online payment verified successfully via {provider} ({provider_payment_id or payment.reference}).",

            )

            msg = 'Payment verified successfully. Order confirmed.'

        else:

            order.payment_status = 'FAILED'

            order.save(update_fields=['payment_status', 'updated_at'])

            OrderStatusHistory.objects.create(

                order=order,

                old_status=order.status,

                new_status=order.status,

                notes=f"Online payment recorded as failed via {provider}.",

            )

            msg = 'Payment recorded as failed.'



        payment.save()



        if previous_payment_status != status_val:

            Notification.objects.create(

                user=profile,

                notification_type='PAYMENT',

                title='Payment successful' if status_val == 'PAID' else 'Payment failed',

                message=(

                    f'Payment for order {order.order_number} was completed successfully.'

                    if status_val == 'PAID'

                    else f'Payment for order {order.order_number} failed. Please try again.'

                ),

                order=order,

                data={

                    'order_number': order.order_number,

                    'payment_reference': payment.reference,

                    'payment_status': status_val,

                },

            )



    return JsonResponse({

        'success': True,

        'message': msg,

        'payment': payment.to_dict(),

        'order': order.to_dict(),

    }, status=200)





@csrf_exempt

def api_user_payment_status(request, reference=None):

    """

    Get payment and order status by payment reference or order number.



    Endpoint: GET /api/user/payment/status/<reference>/

    Headers: Authorization: Bearer <customer_token>

    """

    if request.method != 'GET':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use GET.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    ref = (reference or request.GET.get('reference', '')).strip()

    if not ref:

        return JsonResponse({

            'success': False,

            'message': 'Payment reference or order number is required.',

        }, status=400)



    payment = PaymentTransaction.objects.filter(

        Q(reference=ref) | Q(order__order_number=ref),

        customer=profile,

    ).select_related('order').first()



    if not payment:

        return JsonResponse({

            'success': False,

            'message': f"Payment record '{ref}' was not found for this customer.",

        }, status=404)



    return JsonResponse({

        'success': True,

        'payment': payment.to_dict(),

        'order': payment.order.to_dict(),

    }, status=200)





@csrf_exempt

def api_user_orders_list(request):

    """

    List all orders placed by the authenticated customer.



    Endpoint: GET /api/user/orders/

    Headers: Authorization: Bearer <customer_token>

    """

    if request.method != 'GET':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use GET.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    status_filter = request.GET.get('status', '').strip().upper()

    orders_qs = Order.objects.filter(customer=profile).prefetch_related('items', 'payment_transaction').order_by('-created_at')

    if status_filter and status_filter != 'ALL':

        orders_qs = orders_qs.filter(status=status_filter)



    orders_data = [ord_obj.to_dict() for ord_obj in orders_qs]

    return JsonResponse({

        'success': True,

        'count': len(orders_data),

        'orders': orders_data,

    }, status=200)





@csrf_exempt

def api_user_order_detail(request, order_id):

    """

    Get detailed breakdown of a single order owned by the authenticated customer.



    Endpoint: GET /api/user/orders/<int:order_id>/

    Headers: Authorization: Bearer <customer_token>

    """

    if request.method != 'GET':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use GET.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    order = Order.objects.filter(pk=order_id, customer=profile).prefetch_related('items', 'payment_transaction').first()

    if not order:

        return JsonResponse({

            'success': False,

            'message': f"Order with ID '{order_id}' was not found for this customer.",

        }, status=404)



    history = [

        {

            'old_status': h.old_status,

            'new_status': h.new_status,

            'notes': h.notes,

            'created_at': h.created_at.isoformat(),

        }

        for h in OrderStatusHistory.objects.filter(order=order).order_by('-created_at')

    ]



    order_dict = order.to_dict()

    order_dict['timeline'] = history



    return JsonResponse({

        'success': True,

        'order': order_dict,

    }, status=200)





def _parse_notification_pagination(request):

    try:

        page = int(request.GET.get('page', 1))

        limit = int(request.GET.get('limit', 20))

        if page < 1 or limit < 1:

            raise ValueError

        return page, min(limit, 100), None

    except (TypeError, ValueError):

        return None, None, JsonResponse({

            'success': False,

            'message': 'page and limit must be positive integers.',

        }, status=400)





def api_user_notifications_list(request):

    """List customer notifications with status/type filters and pagination."""

    if request.method != 'GET':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use GET.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    page, limit, pagination_error = _parse_notification_pagination(request)

    if pagination_error:

        return pagination_error



    status_filter = request.GET.get('status', 'all').strip().lower()

    if status_filter not in ['all', 'read', 'unread']:

        return JsonResponse({

            'success': False,

            'message': "status must be 'all', 'read', or 'unread'.",

        }, status=400)



    type_filter = request.GET.get('type', '').strip().upper()

    valid_types = {choice[0] for choice in Notification.TYPE_CHOICES}

    if type_filter and type_filter not in valid_types:

        return JsonResponse({

            'success': False,

            'message': f"type must be one of: {', '.join(sorted(valid_types))}.",

        }, status=400)



    notifications = Notification.objects.filter(user=profile).select_related('order')

    if status_filter == 'read':

        notifications = notifications.filter(is_read=True)

    elif status_filter == 'unread':

        notifications = notifications.filter(is_read=False)

    if type_filter:

        notifications = notifications.filter(notification_type=type_filter)



    total_count = notifications.count()

    total_pages = (total_count + limit - 1) // limit if total_count else 0

    offset = (page - 1) * limit

    page_items = list(notifications[offset:offset + limit])



    return JsonResponse({

        'success': True,

        'total_count': total_count,

        'unread_count': Notification.objects.filter(user=profile, is_read=False).count(),

        'page': page,

        'limit': limit,

        'total_pages': total_pages,

        'has_next': page < total_pages,

        'notifications': [notification.to_dict() for notification in page_items],

    }, status=200)





def api_user_notifications_unread_count(request):

    """Return a lightweight unread badge count for the customer app."""

    if request.method != 'GET':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use GET.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    return JsonResponse({

        'success': True,

        'unread_count': Notification.objects.filter(user=profile, is_read=False).count(),

    }, status=200)





@csrf_exempt

def api_user_notification_mark_read(request, notification_id):

    """Mark one customer-owned notification as read."""

    if request.method not in ['POST', 'PATCH']:

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use POST or PATCH.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    notification = Notification.objects.select_related('order').filter(

        pk=notification_id,

        user=profile,

    ).first()

    if not notification:

        return JsonResponse({

            'success': False,

            'message': f"Notification with ID '{notification_id}' was not found.",

        }, status=404)



    notification.mark_as_read()

    return JsonResponse({

        'success': True,

        'message': 'Notification marked as read.',

        'notification': notification.to_dict(),

        'unread_count': Notification.objects.filter(user=profile, is_read=False).count(),

    }, status=200)





@csrf_exempt

def api_user_notifications_mark_all_read(request):

    """Mark all unread notifications owned by the customer as read."""

    if request.method not in ['POST', 'PATCH']:

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use POST or PATCH.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    updated_count = Notification.objects.filter(user=profile, is_read=False).update(

        is_read=True,

        read_at=timezone.now(),

    )

    return JsonResponse({

        'success': True,

        'message': 'All notifications marked as read.',

        'updated_count': updated_count,

        'unread_count': 0,

    }, status=200)







def _customer_wishlist_items(profile):

    return list(

        WishlistItem.objects.filter(user=profile)

        .select_related('product', 'product__vendor', 'product__category', 'variant')

        .order_by('-created_at', '-id')

    )





@csrf_exempt

def api_user_wishlist_add(request):

    """

    Add a product or exact product variant to the customer's wishlist.



    Endpoint: POST /api/user/wishlist/add/

    Body: {"product_id": 81, "variant_id": 16}

    """

    if request.method != 'POST':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use POST.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    data = _parse_request_data(request)

    try:

        product_id = int(data.get('product_id', ''))

        if product_id <= 0:

            raise ValueError

    except (TypeError, ValueError):

        return JsonResponse({

            'success': False,

            'message': 'product_id must be a valid positive integer.',

        }, status=400)



    raw_variant_id = data.get('variant_id')

    variant_id = None

    if raw_variant_id not in (None, ''):

        try:

            variant_id = int(raw_variant_id)

            if variant_id <= 0:

                raise ValueError

        except (TypeError, ValueError):

            return JsonResponse({

                'success': False,

                'message': 'variant_id must be a valid positive integer.',

            }, status=400)



    product = Product.objects.select_related('vendor', 'category').filter(pk=product_id).first()

    if not product:

        return JsonResponse({

            'success': False,

            'message': f"Product with ID '{product_id}' was not found.",

        }, status=404)

    if not _is_customer_product_available(product):

        return JsonResponse({

            'success': False,

            'message': 'This product is currently unavailable and cannot be added to the wishlist.',

        }, status=400)



    has_variants = ProductVariant.objects.filter(product=product).exists()

    variant = None

    if has_variants:

        if variant_id is None:

            return JsonResponse({

                'success': False,

                'message': 'variant_id is required for this product. Please select a color, size, or material.',

            }, status=400)

        variant = ProductVariant.objects.filter(

            pk=variant_id,

            product=product,

            is_active=True,

        ).first()

        if not variant:

            return JsonResponse({

                'success': False,

                'message': f"Active variant with ID '{variant_id}' was not found for this product.",

            }, status=404)

    elif variant_id is not None:

        return JsonResponse({

            'success': False,

            'message': 'This product does not have variants. Remove variant_id and try again.',

        }, status=400)



    wishlist_item, created = WishlistItem.objects.get_or_create(

        user=profile,

        product=product,

        variant=variant,

    )

    wishlist_item = WishlistItem.objects.select_related(

        'product', 'product__vendor', 'product__category', 'variant'

    ).get(pk=wishlist_item.pk)



    return JsonResponse({

        'success': True,

        'message': (

            'Product added to wishlist successfully.'

            if created else 'Product is already in your wishlist.'

        ),

        'already_exists': not created,

        'wishlist_item': wishlist_item.to_dict(),

        'total_items': WishlistItem.objects.filter(user=profile).count(),

    }, status=201 if created else 200)





def api_user_wishlist_list(request):

    """Return every product saved in the authenticated customer's wishlist."""

    if request.method != 'GET':

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use GET.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    wishlist_items = _customer_wishlist_items(profile)

    return JsonResponse({

        'success': True,

        'total_items': len(wishlist_items),

        'wishlist': [item.to_dict() for item in wishlist_items],

    }, status=200)





@csrf_exempt

def api_user_wishlist_remove(request, product_id, variant_id=None):

    """Remove a product or exact product variant from the customer's wishlist."""

    if request.method not in ['DELETE', 'POST']:

        return JsonResponse({

            'success': False,

            'message': 'Method not allowed. Use DELETE or POST.',

        }, status=405)



    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    if variant_id is None:

        raw_variant_id = request.GET.get('variant_id')

        if raw_variant_id not in (None, ''):

            try:

                variant_id = int(raw_variant_id)

                if variant_id <= 0:

                    raise ValueError

            except (TypeError, ValueError):

                return JsonResponse({

                    'success': False,

                    'message': 'variant_id must be a valid positive integer.',

                }, status=400)



    wishlist_query = WishlistItem.objects.filter(user=profile, product_id=product_id)

    if variant_id is not None:

        wishlist_query = wishlist_query.filter(variant_id=variant_id)

    else:

        wishlist_query = wishlist_query.filter(variant__isnull=True)



    wishlist_item = wishlist_query.first()

    if not wishlist_item:

        return JsonResponse({

            'success': False,

            'message': (

                f"Variant with ID '{variant_id}' for product '{product_id}' is not in your wishlist."

                if variant_id is not None

                else f"Product with ID '{product_id}' is not in your wishlist."

            ),

        }, status=404)



    wishlist_item_id = wishlist_item.id

    wishlist_item.delete()

    return JsonResponse({

        'success': True,

        'message': 'Product removed from wishlist successfully.',

        'removed_wishlist_item_id': wishlist_item_id,

        'product_id': product_id,

        'variant_id': variant_id,

        'total_items': WishlistItem.objects.filter(user=profile).count(),

    }, status=200)





def api_user_order_tracking(request, order_id):

    """Return item-level fulfillment and courier tracking for a customer order."""

    if request.method != 'GET':

        return JsonResponse({'success': False, 'message': 'Method not allowed. Use GET.'}, status=405)

    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    order = Order.objects.filter(pk=order_id, customer=profile).first()

    if not order:

        return JsonResponse({

            'success': False,

            'message': f"Order with ID '{order_id}' was not found for this customer.",

        }, status=404)



    items = order.items.select_related('product', 'variant', 'vendor')

    history = order.status_history.order_by('-created_at')

    return JsonResponse({

        'success': True,

        'order_id': order.id,

        'order_number': order.order_number,

        'order_status': order.status,

        'payment_status': order.payment_status,

        'items': [{

            'order_item_id': item.id,

            'product_id': item.product_id,

            'product_name': item.product_name,

            'variant_id': item.variant_id,

            'variant_title': item.variant_title or None,

            'status': item.status,

            'courier_name': item.courier_name or None,

            'tracking_number': item.tracking_number or None,

            'dispatch_date': item.dispatch_date.isoformat() if item.dispatch_date else None,

            'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None,

        } for item in items],

        'timeline': [entry.to_dict() for entry in history],

        'last_updated': order.updated_at.isoformat() if order.updated_at else None,

    }, status=200)





@csrf_exempt

def api_user_order_request_create(request, order_id):

    """Submit a cancellation request or return request for a customer-owned order."""

    if request.method != 'POST':

        return JsonResponse({'success': False, 'message': 'Method not allowed. Use POST.'}, status=405)

    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    order = Order.objects.filter(pk=order_id, customer=profile).first()

    if not order:

        return JsonResponse({

            'success': False,

            'message': f"Order with ID '{order_id}' was not found for this customer.",

        }, status=404)



    data = _parse_request_data(request)

    request_type = str(data.get('request_type', '')).strip().upper()

    if request_type not in ['CANCEL', 'RETURN']:

        return JsonResponse({

            'success': False,

            'message': "request_type must be either 'CANCEL' or 'RETURN'.",

        }, status=400)

    reason = str(data.get('reason', '')).strip()

    details = str(data.get('details', '')).strip()

    if not reason:

        return JsonResponse({'success': False, 'message': 'reason is required.'}, status=400)

    if len(reason) > 255:

        return JsonResponse({'success': False, 'message': 'reason cannot exceed 255 characters.'}, status=400)



    order_item = None

    raw_order_item_id = data.get('order_item_id')

    if raw_order_item_id not in (None, ''):

        try:

            order_item_id = int(raw_order_item_id)

            if order_item_id <= 0:

                raise ValueError

        except (TypeError, ValueError):

            return JsonResponse({

                'success': False,

                'message': 'order_item_id must be a valid positive integer.',

            }, status=400)

        order_item = order.items.filter(pk=order_item_id).first()

        if not order_item:

            return JsonResponse({

                'success': False,

                'message': f"Order item '{order_item_id}' was not found in this order.",

            }, status=404)



    target_status = order_item.status if order_item else order.status

    if request_type == 'CANCEL' and target_status not in ['PENDING', 'CONFIRMED', 'PROCESSING']:

        return JsonResponse({

            'success': False,

            'message': f"Cancellation cannot be requested when the status is '{target_status}'.",

        }, status=400)

    if request_type == 'RETURN' and target_status != 'DELIVERED':

        return JsonResponse({

            'success': False,

            'message': 'A return can only be requested after delivery.',

        }, status=400)



    if OrderRequest.objects.filter(

        customer=profile,

        order=order,

        order_item=order_item,

        request_type=request_type,

        status='PENDING',

    ).exists():

        return JsonResponse({

            'success': False,

            'message': f'A pending {request_type.lower()} request already exists for this selection.',

        }, status=409)



    order_request = OrderRequest.objects.create(

        customer=profile,

        order=order,

        order_item=order_item,

        request_type=request_type,

        reason=reason,

        details=details,

    )

    Notification.objects.create(

        user=profile,

        order=order,

        notification_type='CANCELLATION' if request_type == 'CANCEL' else 'RETURN',

        title=f'{order_request.get_request_type_display()} request received',

        message=f'Your request {order_request.request_number} is pending review.',

        data={

            'request_id': order_request.id,

            'request_number': order_request.request_number,

            'order_item_id': order_item.id if order_item else None,

        },

    )

    return JsonResponse({

        'success': True,

        'message': f'{order_request.get_request_type_display()} request submitted successfully.',

        'request': order_request.to_dict(),

    }, status=201)





def api_user_order_request_list(request):

    """List cancellation and return requests submitted by the customer."""

    if request.method != 'GET':

        return JsonResponse({'success': False, 'message': 'Method not allowed. Use GET.'}, status=405)

    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error



    requests_query = OrderRequest.objects.filter(customer=profile).select_related('order', 'order_item')

    request_type = str(request.GET.get('request_type', '')).strip().upper()

    status_filter = str(request.GET.get('status', '')).strip().upper()

    if request_type:

        if request_type not in ['CANCEL', 'RETURN']:

            return JsonResponse({'success': False, 'message': 'Invalid request_type filter.'}, status=400)

        requests_query = requests_query.filter(request_type=request_type)

    if status_filter:

        valid_statuses = {choice[0] for choice in OrderRequest.STATUS_CHOICES}

        if status_filter not in valid_statuses:

            return JsonResponse({'success': False, 'message': 'Invalid status filter.'}, status=400)

        requests_query = requests_query.filter(status=status_filter)

    request_list = [order_request.to_dict() for order_request in requests_query]

    return JsonResponse({

        'success': True,

        'total_count': len(request_list),

        'requests': request_list,

    }, status=200)





@csrf_exempt

def api_product_reviews(request, product_id):

    """List approved product reviews or create an authenticated customer review."""

    product = Product.objects.select_related('vendor', 'category').filter(pk=product_id).first()

    if not product:

        return JsonResponse({'success': False, 'message': f"Product '{product_id}' was not found."}, status=404)



    if request.method == 'GET':

        reviews_query = ProductReview.objects.filter(product=product, is_approved=True).select_related('user', 'variant')

        reviews = [review.to_dict() for review in reviews_query]

        average_rating = reviews_query.aggregate(value=Avg('rating'))['value'] or 0

        return JsonResponse({

            'success': True,

            'product_id': product.id,

            'product_name': product.name,

            'average_rating': round(float(average_rating), 2),

            'total_reviews': len(reviews),

            'rating_distribution': {

                str(rating): reviews_query.filter(rating=rating).count()

                for rating in range(5, 0, -1)

            },

            'reviews': reviews,

        }, status=200)



    if request.method != 'POST':

        return JsonResponse({'success': False, 'message': 'Method not allowed. Use GET or POST.'}, status=405)

    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error

    data = _parse_request_data(request)

    try:

        rating = int(data.get('rating', ''))

        if rating < 1 or rating > 5:

            raise ValueError

    except (TypeError, ValueError):

        return JsonResponse({'success': False, 'message': 'rating must be an integer from 1 to 5.'}, status=400)

    title = str(data.get('title', '')).strip()

    comment = str(data.get('comment', '')).strip()

    if len(title) > 150:

        return JsonResponse({'success': False, 'message': 'title cannot exceed 150 characters.'}, status=400)



    variant = None

    raw_variant_id = data.get('variant_id')

    if raw_variant_id not in (None, ''):

        try:

            variant_id = int(raw_variant_id)

        except (TypeError, ValueError):

            return JsonResponse({'success': False, 'message': 'variant_id must be a valid integer.'}, status=400)

        variant = ProductVariant.objects.filter(pk=variant_id, product=product).first()

        if not variant:

            return JsonResponse({

                'success': False,

                'message': f"Variant '{variant_id}' was not found for this product.",

            }, status=404)



    if ProductReview.objects.filter(user=profile, product=product).exists():

        return JsonResponse({

            'success': False,

            'message': 'You have already reviewed this product. Use the update API to change it.',

        }, status=409)



    delivered_items = OrderItem.objects.filter(

        order__customer=profile,

        product=product,

        status='DELIVERED',

    )

    if variant:

        delivered_items = delivered_items.filter(variant=variant)

    review = ProductReview.objects.create(

        user=profile,

        product=product,

        variant=variant,

        rating=rating,

        title=title,

        comment=comment,

        is_verified_purchase=delivered_items.exists(),

    )

    review = ProductReview.objects.select_related('user', 'product', 'variant').get(pk=review.pk)

    return JsonResponse({

        'success': True,

        'message': 'Review submitted successfully.',

        'review': review.to_dict(),

    }, status=201)





@csrf_exempt

def api_user_review_update(request, review_id):

    if request.method not in ['PUT', 'PATCH', 'POST']:

        return JsonResponse({'success': False, 'message': 'Method not allowed. Use PUT, PATCH, or POST.'}, status=405)

    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error

    review = ProductReview.objects.select_related('user', 'product', 'variant').filter(

        pk=review_id,

        user=profile,

    ).first()

    if not review:

        return JsonResponse({'success': False, 'message': f"Review '{review_id}' was not found."}, status=404)

    data = _parse_request_data(request)

    if 'rating' in data:

        try:

            rating = int(data.get('rating'))

            if rating < 1 or rating > 5:

                raise ValueError

            review.rating = rating

        except (TypeError, ValueError):

            return JsonResponse({'success': False, 'message': 'rating must be an integer from 1 to 5.'}, status=400)

    if 'title' in data:

        title = str(data.get('title', '')).strip()

        if len(title) > 150:

            return JsonResponse({'success': False, 'message': 'title cannot exceed 150 characters.'}, status=400)

        review.title = title

    if 'comment' in data:

        review.comment = str(data.get('comment', '')).strip()

    review.save()

    return JsonResponse({'success': True, 'message': 'Review updated successfully.', 'review': review.to_dict()}, status=200)





@csrf_exempt

def api_user_review_delete(request, review_id):

    if request.method not in ['DELETE', 'POST']:

        return JsonResponse({'success': False, 'message': 'Method not allowed. Use DELETE or POST.'}, status=405)

    profile, auth_error = _require_user_auth(request)

    if auth_error:

        return auth_error

    review = ProductReview.objects.filter(pk=review_id, user=profile).first()

    if not review:

        return JsonResponse({'success': False, 'message': f"Review '{review_id}' was not found."}, status=404)

    product_id = review.product_id

    review.delete()

    return JsonResponse({

        'success': True,

        'message': 'Review deleted successfully.',

        'deleted_review_id': review_id,

        'product_id': product_id,

    }, status=200)





def _managed_variant_product(request, product_id, action='manage variants for'):

    product = Product.objects.select_related('vendor', 'category').filter(pk=product_id).first()

    if not product:

        return None, None, JsonResponse({

            "success": False,

            "message": f"Product with ID '{product_id}' not found."

        }, status=404)



    vendor = None

    if request.path.startswith('/api/vendor/'):

        vendor, auth_error = _require_vendor_auth(request)

        if auth_error:

            return None, None, auth_error

        ownership_error = _check_vendor_ownership(vendor, product, action_name=action)

        if ownership_error:

            return None, None, ownership_error

    return product, vendor, None





def _managed_variant(request, variant_id, action='manage'):

    variant = ProductVariant.objects.select_related('product', 'product__vendor').filter(pk=variant_id).first()

    if not variant:

        return None, None, JsonResponse({

            "success": False,

            "message": f"Variant with ID '{variant_id}' not found."

        }, status=404)



    vendor = None

    if request.path.startswith('/api/vendor/'):

        vendor, auth_error = _require_vendor_auth(request)

        if auth_error:

            return None, None, auth_error

        ownership_error = _check_vendor_ownership(vendor, variant.product, action_name=action)

        if ownership_error:

            return None, None, ownership_error

    return variant, vendor, None





def _variant_image_from_request(request, data, variant):

    image_file = request.FILES.get('image') or request.FILES.get('variant_image')

    if image_file:

        variant.image = image_file

        return



    image_value = data.get('image') or data.get('image_url')

    if not image_value or not isinstance(image_value, str):

        return

    image_value = image_value.strip()

    if image_value.startswith('data:image') and ';base64,' in image_value:

        try:

            image_format, image_data = image_value.split(';base64,', 1)

            extension = image_format.split('/')[-1].split('+')[0]

            file_name = f"variant_{slugify(variant.title)}_{random.randint(1000, 9999)}.{extension}"

            variant.image = ContentFile(base64.b64decode(image_data), name=file_name)

        except Exception:

            pass

    elif image_value:

        variant.image = image_value





def _parse_variant_number(data, field, required=False, integer=False):

    raw_value = data.get(field)

    if raw_value in [None, '']:

        if required:

            return None, f"Field '{field}' is required."

        return None, None

    try:

        value = int(raw_value) if integer else Decimal(str(raw_value))

    except (InvalidOperation, TypeError, ValueError):

        return None, f"Field '{field}' must be a valid {'integer' if integer else 'number'}."

    if not integer and not value.is_finite():

        return None, f"Field '{field}' must be a finite number."

    if value < 0:

        return None, f"Field '{field}' cannot be negative."

    return value, None





@csrf_exempt

def api_product_variant_list(request, product_id):

    """List all variants for a vendor-owned or admin-selected product."""

    if request.method != 'GET':

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    product, vendor, error = _managed_variant_product(request, product_id, action='view variants for')

    if error:

        return error

    variants = list(product.variants.all().order_by('id'))

    return JsonResponse({

        "success": True,

        "product_id": product.id,

        "product_name": product.name,

        "total_variants": len(variants),

        "variants": [variant.to_dict() for variant in variants],

    }, status=200)





@csrf_exempt

def api_product_variant_create(request, product_id):

    """Create a product variant as the owning vendor or an administrator."""

    if request.method != 'POST':

        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)



    product, vendor, error = _managed_variant_product(request, product_id, action='add variants to')

    if error:

        return error

    data = _parse_request_data(request)

    title = str(data.get('title', '')).strip()

    if not title:

        return JsonResponse({"success": False, "message": "Field 'title' is required."}, status=400)



    sku = str(data.get('sku', '')).strip()

    if sku and ProductVariant.objects.filter(sku__iexact=sku).exists():

        return JsonResponse({

            "success": False,

            "message": f"A variant with SKU '{sku}' already exists."

        }, status=400)



    price, error_message = _parse_variant_number(data, 'price')

    if error_message:

        return JsonResponse({"success": False, "message": error_message}, status=400)

    discount_price, error_message = _parse_variant_number(data, 'discount_price')

    if error_message:

        return JsonResponse({"success": False, "message": error_message}, status=400)

    stock_quantity, error_message = _parse_variant_number(data, 'stock_quantity', integer=True)

    if error_message:

        return JsonResponse({"success": False, "message": error_message}, status=400)



    is_active = True

    if 'is_active' in data:

        is_active, is_valid = _parse_boolean(data['is_active'])

        if not is_valid:

            return JsonResponse({"success": False, "message": "Field 'is_active' must be true or false."}, status=400)



    with transaction.atomic():

        variant = ProductVariant(

            product=product,

            title=title,

            color=str(data.get('color', '')).strip(),

            size=str(data.get('size', '')).strip(),

            material=str(data.get('material', '')).strip(),

            sku=sku,

            price=price,

            discount_price=discount_price,

            stock_quantity=stock_quantity or 0,

            is_active=is_active,

        )

        _variant_image_from_request(request, data, variant)

        variant.save()

        if variant.stock_quantity > 0:

            StockLog.objects.create(

                product=product,

                variant=variant,

                vendor=product.vendor,

                movement_type='RESTOCK',

                quantity_changed=variant.stock_quantity,

                previous_stock=0,

                new_stock=variant.stock_quantity,

                reason='Initial stock upon variant creation',

            )



    product.refresh_from_db()

    return JsonResponse({

        "success": True,

        "message": "Product variant created successfully",

        "variant": variant.to_dict(),

        "product_stock_quantity": product.stock_quantity,

    }, status=201)





@csrf_exempt

def api_product_variant_detail(request, variant_id):

    """Return one variant to its owning vendor or an administrator."""

    if request.method != 'GET':

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)

    variant, vendor, error = _managed_variant(request, variant_id, action='view this variant for')

    if error:

        return error

    return JsonResponse({"success": True, "variant": variant.to_dict()}, status=200)





@csrf_exempt

def api_product_variant_update(request, variant_id):

    """Update variant attributes, price, image, activity, or stock."""

    if request.method not in ['POST', 'PUT', 'PATCH']:

        return JsonResponse({

            "success": False,

            "message": "Method not allowed. Use POST, PUT, or PATCH."

        }, status=405)

    variant, vendor, error = _managed_variant(request, variant_id, action='update this variant for')

    if error:

        return error

    data = _parse_request_data(request)



    if 'title' in data:

        title = str(data['title']).strip()

        if not title:

            return JsonResponse({"success": False, "message": "Field 'title' cannot be empty."}, status=400)

        variant.title = title

    for field in ['color', 'size', 'material']:

        if field in data:

            setattr(variant, field, str(data[field]).strip())

    if 'sku' in data:

        sku = str(data['sku']).strip()

        if not sku:

            return JsonResponse({"success": False, "message": "Field 'sku' cannot be empty."}, status=400)

        if ProductVariant.objects.filter(sku__iexact=sku).exclude(pk=variant.pk).exists():

            return JsonResponse({"success": False, "message": f"A variant with SKU '{sku}' already exists."}, status=400)

        variant.sku = sku



    for field in ['price', 'discount_price']:

        if field in data:

            raw_value = data[field]

            if raw_value in [None, '', 'null']:

                setattr(variant, field, None)

            else:

                value, error_message = _parse_variant_number(data, field)

                if error_message:

                    return JsonResponse({"success": False, "message": error_message}, status=400)

                setattr(variant, field, value)



    previous_stock = variant.stock_quantity

    if 'stock_quantity' in data:

        stock_quantity, error_message = _parse_variant_number(data, 'stock_quantity', integer=True)

        if error_message:

            return JsonResponse({"success": False, "message": error_message}, status=400)

        variant.stock_quantity = stock_quantity

    if 'is_active' in data:

        is_active, is_valid = _parse_boolean(data['is_active'])

        if not is_valid:

            return JsonResponse({"success": False, "message": "Field 'is_active' must be true or false."}, status=400)

        variant.is_active = is_active

    if str(data.get('remove_image', '')).strip().lower() in ['true', '1', 'yes']:

        variant.image = None

    else:

        _variant_image_from_request(request, data, variant)



    with transaction.atomic():

        variant.save()

        if variant.stock_quantity != previous_stock:

            StockLog.objects.create(

                product=variant.product,

                variant=variant,

                vendor=variant.product.vendor,

                movement_type='CORRECTION',

                quantity_changed=variant.stock_quantity - previous_stock,

                previous_stock=previous_stock,

                new_stock=variant.stock_quantity,

                reason='Stock updated through variant management API',

            )



    variant.product.refresh_from_db()

    return JsonResponse({

        "success": True,

        "message": "Product variant updated successfully",

        "variant": variant.to_dict(),

        "product_stock_quantity": variant.product.stock_quantity,

    }, status=200)





@csrf_exempt

def api_product_variant_delete(request, variant_id):

    """Delete a variant as the owning vendor or an administrator."""

    if request.method not in ['DELETE', 'POST']:

        return JsonResponse({"success": False, "message": "Method not allowed. Use DELETE or POST."}, status=405)

    variant, vendor, error = _managed_variant(request, variant_id, action='delete this variant for')

    if error:

        return error

    product = variant.product

    deleted_id = variant.id

    deleted_title = variant.title

    variant.delete()

    product.refresh_from_db()

    return JsonResponse({

        "success": True,

        "message": "Product variant deleted successfully",

        "deleted_variant_id": deleted_id,

        "deleted_variant_title": deleted_title,

        "product_stock_quantity": product.stock_quantity,

    }, status=200)





@csrf_exempt

def api_user_refresh_token(request):

    """

    API: Refresh / Rotate Customer Bearer Auth Token (Optional)

    Note: Bearer tokens are permanent and never expire automatically.

    This endpoint is provided for clients who wish to manually rotate their active Bearer token.

    Endpoint: POST /api/user/refresh-token/

    Headers: Authorization: Bearer <current_token>

    Body (optional fallback): {"token": "..."}

    """

    if request.method != "POST":

        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)



    data = _parse_request_data(request)

    body_token = str(data.get("token") or data.get("refresh_token") or "").strip()



    profile = None

    if body_token:

        profile = UserProfile.objects.select_related('user').filter(auth_token=body_token).first()

    else:

        auth_header = request.headers.get('Authorization', '') or request.META.get('HTTP_AUTHORIZATION', '')

        parts = auth_header.split()

        if len(parts) == 2 and parts[0].lower() in ['bearer', 'token']:

            profile = UserProfile.objects.select_related('user').filter(auth_token=parts[1].strip()).first()

        elif request.user.is_authenticated and hasattr(request.user, 'customer_profile'):

            profile = request.user.customer_profile



    if not profile:

        return JsonResponse({

            "success": False,

            "message": "Invalid or missing token. Please provide a valid Bearer token."

        }, status=401)



    if not profile.is_active or (profile.user and not profile.user.is_active):

        return JsonResponse({

            "success": False,

            "message": "Your account has been deactivated by administrator. Please contact support."

        }, status=403)



    new_token = profile.generate_new_token()

    return JsonResponse({

        "success": True,

        "message": "Token refreshed successfully",

        "auth_token": new_token,

        "token": new_token,

        "user": profile.to_dict()

    }, status=200)





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

            vendor = VendorProfile.objects.select_related('user').filter(
                auth_token=token,
                status='APPROVED',
                user__is_active=True,
            ).first()

            if vendor:

                return vendor



    if (
        request.user.is_authenticated
        and request.user.is_active
        and hasattr(request.user, 'vendor_profile')
        and request.user.vendor_profile.status == 'APPROVED'
    ):

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



    if (
        user_obj
        and user_obj.check_password(password)
        and hasattr(user_obj, 'vendor_profile')
        and user_obj.vendor_profile.status == 'BLOCKED'
    ):

        return JsonResponse({

            "success": False,

            "status": "BLOCKED",

            "vendor_code": user_obj.vendor_profile.vendor_code,

            "message": "Seller access has been blocked by the marketplace administrator. Please contact support."

        }, status=403)



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



    # Handle image upload (multipart binary file, base64 data, or image_url string)

    if request.FILES.get("image"):

        product.image = request.FILES["image"]

    elif request.FILES.get("product_image"):

        product.image = request.FILES["product_image"]

    elif "image" in data and isinstance(data["image"], str):

        img_val = data["image"].strip()

        if img_val.startswith("data:image"):

            try:

                fmt, imgstr = img_val.split(";base64,")

                ext = fmt.split("/")[-1].split("+")[0]

                product.image = ContentFile(base64.b64decode(imgstr), name=f"{slugify(name)}_{random.randint(1000, 9999)}.{ext}")

            except Exception:

                pass

        elif img_val:

            product.image = img_val

    elif data.get("image_url"):

        product.image = str(data["image_url"]).strip()



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



    include_inactive_variants = (

        request.path.startswith('/api/vendor/') or request.path.startswith('/api/admin/')

    )

    variants = product.variants.all()

    if not include_inactive_variants:

        variants = variants.filter(is_active=True)

    variants = list(variants.order_by('id'))

    product_data = product.to_dict()

    product_data.update({

        'available_colors': sorted({variant.color for variant in variants if variant.color}),

        'available_sizes': sorted({variant.size for variant in variants if variant.size}),

        'available_materials': sorted({variant.material for variant in variants if variant.material}),

        'variants': [variant.to_dict() for variant in variants],

    })



    return JsonResponse({

        "success": True,

        "product": product_data

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

        if product.has_variants:

            return JsonResponse({

                "success": False,

                "message": "This product uses variants. Update stock on the individual variant instead."

            }, status=400)

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



    # Update image (multipart binary file, base64 data, or image_url string)

    if request.FILES.get("image"):

        product.image = request.FILES["image"]

    elif request.FILES.get("product_image"):

        product.image = request.FILES["product_image"]

    elif "image" in data and isinstance(data["image"], str):

        img_val = data["image"].strip()

        if img_val.startswith("data:image"):

            try:

                fmt, imgstr = img_val.split(";base64,")

                ext = fmt.split("/")[-1].split("+")[0]

                product.image = ContentFile(base64.b64decode(imgstr), name=f"{slugify(product.name)}_{random.randint(1000, 9999)}.{ext}")

            except Exception:

                pass

        elif img_val:

            product.image = img_val

    elif data.get("image_url"):

        product.image = str(data["image_url"]).strip()



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



    total_skus = 0

    total_units = 0

    healthy_count = 0

    low_stock_count = 0

    out_of_stock_count = 0

    total_valuation = 0.0



    for prod in qs:

        total_skus += prod.active_variant_count if prod.has_variants else 1

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

        qs = qs.filter(

            Q(name__icontains=search) |

            Q(sku__icontains=search) |

            Q(variants__title__icontains=search) |

            Q(variants__sku__icontains=search)

        ).distinct()



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

            "has_variants": prod.has_variants,

            "variant_count": prod.active_variant_count,

            "variants": [variant.to_dict() for variant in prod.variants.all().order_by('id')],

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

      - variant_id: integer (required when the product has variants)

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



    variant = None

    raw_variant_id = data.get('variant_id')

    if raw_variant_id not in [None, '']:

        try:

            variant_id = int(raw_variant_id)

        except (TypeError, ValueError):

            return JsonResponse({"success": False, "message": "Field 'variant_id' must be a valid integer."}, status=400)

        variant = ProductVariant.objects.filter(pk=variant_id, product=product).first()

        if not variant:

            return JsonResponse({

                "success": False,

                "message": f"Variant with ID '{variant_id}' was not found for this product."

            }, status=404)

    elif product.has_variants:

        return JsonResponse({

            "success": False,

            "message": "This product uses variants. Field 'variant_id' is required for stock adjustment."

        }, status=400)



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



    stock_target = variant or product

    prev_stock = stock_target.stock_quantity



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

                Product.objects.filter(pk=product.pk).update(low_stock_threshold=val_th)

        except (ValueError, TypeError):

            pass



    stock_target.stock_quantity = new_stock

    stock_target.save()

    product.refresh_from_db()



    stock_log = StockLog.objects.create(

        product=product,

        variant=variant,

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

        "message": (

            f"Stock for variant '{variant.title}' adjusted from {prev_stock} to {new_stock} units."

            if variant else

            f"Stock for '{product.name}' adjusted from {prev_stock} to {new_stock} units."

        ),

        "product": product.to_dict(),

        "variant": variant.to_dict() if variant else None,

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



    qs = StockLog.objects.all().select_related('product', 'variant', 'vendor')



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



    variant_id = request.GET.get('variant_id')

    if variant_id:

        try:

            qs = qs.filter(variant_id=int(variant_id))

        except (TypeError, ValueError):

            return JsonResponse({

                "success": False,

                "message": "Query parameter 'variant_id' must be a valid integer."

            }, status=400)



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





# =============================================================================

# Vendor Orders & Customer Details REST APIs

# =============================================================================



def _get_vendor_balance_summary(vendor):

    """

    Calculates vendor earnings, pending balance, and current available withdrawal balance.

    """

    earnings_qs = VendorEarning.objects.filter(vendor=vendor)

    lifetime_gross = float(earnings_qs.aggregate(total=Sum('gross_amount'))['total'] or 0.0)

    total_commission = float(earnings_qs.aggregate(total=Sum('commission_amount'))['total'] or 0.0)

    lifetime_net = float(earnings_qs.aggregate(total=Sum('net_amount'))['total'] or 0.0)



    cleared_earnings = float(earnings_qs.filter(status='AVAILABLE').aggregate(total=Sum('net_amount'))['total'] or 0.0)

    pending_clearance = float(earnings_qs.filter(status='PENDING').aggregate(total=Sum('net_amount'))['total'] or 0.0)



    payouts_qs = VendorPayout.objects.filter(vendor=vendor)

    settled_payouts = float(payouts_qs.filter(status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0.0)

    pending_payouts = float(payouts_qs.filter(status__in=['PENDING', 'PROCESSING']).aggregate(total=Sum('amount'))['total'] or 0.0)



    available_balance = max(round(cleared_earnings - settled_payouts - pending_payouts, 2), 0.0)



    return {

        'lifetime_gross_sales': round(lifetime_gross, 2),

        'platform_commission_rate_percent': 5.0,

        'total_commission_deducted': round(total_commission, 2),

        'lifetime_net_earnings': round(lifetime_net, 2),

        'available_balance': available_balance,

        'pending_clearance': round(pending_clearance, 2),

        'total_withdrawn': round(settled_payouts, 2),

        'pending_payout_requests': round(pending_payouts, 2),

        'currency': 'INR'

    }





@csrf_exempt

def api_vendor_orders(request):

    """

    API: List Orders for Authenticated Vendor

    Method: GET

    Endpoint: /api/vendor/orders/

    Header: Authorization: Bearer <vendor_token>

    """

    if request.method != "GET":

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    vendor, err_resp = _require_vendor_auth(request)

    if err_resp:

        return err_resp



    order_ids = OrderItem.objects.filter(vendor=vendor).values_list('order_id', flat=True).distinct()

    qs = Order.objects.filter(id__in=order_ids).prefetch_related('items')



    status_param = request.GET.get('status', '').strip().upper()

    if status_param and status_param != 'ALL':

        qs = qs.filter(status=status_param)



    search_query = request.GET.get('search', '').strip()

    if search_query:

        qs = qs.filter(

            Q(order_number__icontains=search_query) |

            Q(customer_name__icontains=search_query) |

            Q(customer_phone__icontains=search_query)

        )



    date_from = request.GET.get('date_from', '').strip()

    if date_from:

        try:

            df = datetime.strptime(date_from, '%Y-%m-%d')

            qs = qs.filter(created_at__gte=df)

        except ValueError:

            pass



    date_to = request.GET.get('date_to', '').strip()

    if date_to:

        try:

            dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)

            qs = qs.filter(created_at__lt=dt)

        except ValueError:

            pass



    ordering = request.GET.get('ordering', '-created_at').strip()

    allowed_orderings = ['created_at', '-created_at', 'total_amount', '-total_amount']

    if ordering in allowed_orderings:

        qs = qs.order_by(ordering)



    limit = 50

    if request.GET.get('limit'):

        try:

            limit = max(1, min(int(request.GET.get('limit')), 200))

        except (ValueError, TypeError):

            pass



    orders_list = [o.to_dict(vendor=vendor) for o in qs[:limit]]



    return JsonResponse({

        "success": True,

        "count": len(orders_list),

        "orders": orders_list

    }, status=200)





@csrf_exempt

def api_vendor_order_detail(request, order_id):

    """

    API: Get Detailed Customer and Order Info (Strictly Scoped to Vendor)

    Method: GET

    Endpoint: /api/vendor/orders/<order_id>/

    Header: Authorization: Bearer <vendor_token>

    """

    if request.method != "GET":

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    vendor, err_resp = _require_vendor_auth(request)

    if err_resp:

        return err_resp



    order = None

    if str(order_id).isdigit():

        order = Order.objects.filter(id=int(order_id)).first()

    if not order:

        order = Order.objects.filter(order_number__iexact=str(order_id).strip()).first()



    if not order:

        return JsonResponse({

            "success": False,

            "message": f"Order '{order_id}' not found."

        }, status=404)



    vendor_items = order.items.filter(vendor=vendor)

    if not vendor_items.exists():

        return JsonResponse({

            "success": False,

            "message": "Access denied. You do not have permission to view this order."

        }, status=403)



    order_data = order.to_dict(vendor=vendor)

    order_data['customer'] = {

        'name': order.customer_name,

        'phone': order.customer_phone,

        'email': order.customer_email or ''

    }

    order_data['shipping_address'] = {

        'address': order.shipping_address,

        'city': order.shipping_city,

        'state': order.shipping_state,

        'pincode': order.shipping_pincode

    }

    order_data['payment'] = {

        'method': order.payment_method,

        'status': order.payment_status

    }



    history_logs = OrderStatusHistory.objects.filter(

        order=order

    ).filter(

        Q(vendor=vendor) | Q(vendor__isnull=True)

    ).order_by('-created_at')



    order_data['status_history'] = [h.to_dict() for h in history_logs]



    return JsonResponse({

        "success": True,

        "order": order_data

    }, status=200)





@csrf_exempt

def api_vendor_order_status_update(request, order_id):

    """

    API: Update Order Status (Processing, Shipped, Delivered, Cancelled)

    Method: POST

    Endpoint: /api/vendor/orders/<order_id>/status/

    Header: Authorization: Bearer <vendor_token>

    """

    if request.method not in ["POST", "PUT"]:

        return JsonResponse({"success": False, "message": "Method not allowed. Use POST or PUT."}, status=405)



    vendor, err_resp = _require_vendor_auth(request)

    if err_resp:

        return err_resp



    order = None

    if str(order_id).isdigit():

        order = Order.objects.filter(id=int(order_id)).first()

    if not order:

        order = Order.objects.filter(order_number__iexact=str(order_id).strip()).first()



    if not order:

        return JsonResponse({"success": False, "message": f"Order '{order_id}' not found."}, status=404)



    vendor_items = order.items.filter(vendor=vendor)

    if not vendor_items.exists():

        return JsonResponse({

            "success": False,

            "message": "Access denied. You do not have permission to modify this order."

        }, status=403)



    data = _parse_request_data(request)

    raw_status = str(data.get("status", "")).strip().upper()

    valid_statuses = ['CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED']

    if raw_status not in valid_statuses:

        return JsonResponse({

            "success": False,

            "message": f"Invalid status '{raw_status}'. Allowed values: {', '.join(valid_statuses)}."

        }, status=400)



    courier_name = str(data.get("courier_name", "")).strip()

    tracking_number = str(data.get("tracking_number", "")).strip()

    notes = str(data.get("notes", "")).strip()



    old_status = order.status

    now = timezone.now()

    previous_item_statuses = {item.id: item.status for item in vendor_items}



    for item in vendor_items:

        item.status = raw_status

        if courier_name:

            item.courier_name = courier_name

        if tracking_number:

            item.tracking_number = tracking_number

        if raw_status == 'SHIPPED' and not item.dispatch_date:

            item.dispatch_date = now

        elif raw_status == 'DELIVERED' and not item.delivery_date:

            item.delivery_date = now

        item.save()



    order.status = raw_status

    if raw_status == 'DELIVERED' and order.payment_method == 'COD':

        order.payment_status = 'PAID'

    order.save()



    OrderStatusHistory.objects.create(

        order=order,

        vendor=vendor,

        old_status=old_status,

        new_status=raw_status,

        notes=notes or f"Order status updated to {raw_status} by {vendor.business_name}"

    )



    if raw_status == 'DELIVERED':

        for item in vendor_items:

            earning, created = VendorEarning.objects.get_or_create(

                vendor=vendor,

                order=order,

                order_item=item,

                defaults={

                    'gross_amount': item.total_price,

                    'commission_rate': item.commission_rate,

                    'commission_amount': item.commission_amount,

                    'net_amount': item.vendor_unit_price * item.quantity,

                    'status': 'AVAILABLE',

                    'cleared_at': now

                }

            )

            if not created:

                earning.status = 'AVAILABLE'

                earning.cleared_at = now

                earning.save()



    elif raw_status == 'CANCELLED':

        for item in vendor_items:

            if previous_item_statuses.get(item.id) == 'CANCELLED':

                continue

            if item.variant:

                prev_st = item.variant.stock_quantity

                item.variant.stock_quantity = prev_st + item.quantity

                item.variant.save()

                StockLog.objects.create(

                    product=item.product,

                    variant=item.variant,

                    vendor=vendor,

                    movement_type='RETURN',

                    quantity_changed=item.quantity,

                    previous_stock=prev_st,

                    new_stock=item.variant.stock_quantity,

                    reason=f"Order {order.order_number} cancelled; {item.quantity} variant units returned to inventory",

                    reference_id=order.order_number

                )

            elif item.product:

                prev_st = item.product.stock_quantity

                item.product.stock_quantity = prev_st + item.quantity

                item.product.save()

                StockLog.objects.create(

                    product=item.product,

                    vendor=vendor,

                    movement_type='RETURN',

                    quantity_changed=item.quantity,

                    previous_stock=prev_st,

                    new_stock=item.product.stock_quantity,

                    reason=f"Order {order.order_number} cancelled; {item.quantity} units returned to inventory",

                    reference_id=order.order_number

                )

            VendorEarning.objects.filter(order=order, order_item=item).update(status='REFUNDED')



    first_item = vendor_items.first()

    return JsonResponse({

        "success": True,

        "message": f"Order status successfully updated to '{raw_status}'.",

        "order_id": order.id,

        "order_number": order.order_number,

        "previous_status": old_status,

        "new_status": raw_status,

        "tracking_info": {

            "courier_name": courier_name or (first_item.courier_name if first_item else ''),

            "tracking_number": tracking_number or (first_item.tracking_number if first_item else ''),

            "dispatch_date": first_item.dispatch_date.isoformat() if (first_item and first_item.dispatch_date) else None

        }

    }, status=200)





# =============================================================================

# Sales & Earnings Analytics REST APIs

# =============================================================================



@csrf_exempt

def api_vendor_sales_overview(request):

    """

    API: Get Vendor Sales Overview & KPIs

    Method: GET

    Endpoint: /api/vendor/sales/overview/

    Header: Authorization: Bearer <vendor_token>

    """

    if request.method != "GET":

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    vendor, err_resp = _require_vendor_auth(request)

    if err_resp:

        return err_resp



    period = request.GET.get('period', 'month').strip().lower()

    now = timezone.now()



    if period == 'today':

        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    elif period == 'week':

        start_date = now - timedelta(days=7)

    elif period == 'month':

        start_date = now - timedelta(days=30)

    elif period == 'year':

        start_date = now - timedelta(days=365)

    else:

        start_date = None



    items_qs = OrderItem.objects.filter(vendor=vendor)

    if start_date:

        items_qs = items_qs.filter(created_at__gte=start_date)



    non_cancelled_items = items_qs.exclude(status='CANCELLED')

    total_revenue = float(non_cancelled_items.aggregate(total=Sum('total_price'))['total'] or 0.0)

    units_sold = int(non_cancelled_items.aggregate(total=Sum('quantity'))['total'] or 0)

    distinct_orders = items_qs.values_list('order_id', flat=True).distinct()

    total_orders = distinct_orders.count()

    aov = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0



    status_counts = {}

    for st_choice, _ in Order.STATUS_CHOICES:

        cnt = Order.objects.filter(id__in=distinct_orders, status=st_choice).count()

        status_counts[st_choice] = cnt



    daily_trend = []

    for i in range(6, -1, -1):

        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)

        day_end = day_start + timedelta(days=1)

        day_items = items_qs.filter(created_at__gte=day_start, created_at__lt=day_end).exclude(status='CANCELLED')

        day_rev = float(day_items.aggregate(total=Sum('total_price'))['total'] or 0.0)

        day_orders = day_items.values_list('order_id', flat=True).distinct().count()

        daily_trend.append({

            "date": day_start.strftime('%Y-%m-%d'),

            "orders": day_orders,

            "revenue": round(day_rev, 2)

        })



    top_prods_data = []

    top_qs = items_qs.exclude(status='CANCELLED').values(

        'product_id', 'product_name', 'product_sku'

    ).annotate(

        units_sold=Sum('quantity'),

        revenue=Sum('total_price')

    ).order_by('-revenue')[:5]



    for tp in top_qs:

        top_prods_data.append({

            'product_id': tp['product_id'],

            'name': tp['product_name'],

            'sku': tp['product_sku'],

            'units_sold': tp['units_sold'],

            'revenue': float(tp['revenue'])

        })



    return JsonResponse({

        "success": True,

        "period": period,

        "kpis": {

            "total_revenue": round(total_revenue, 2),

            "total_orders": total_orders,

            "units_sold": units_sold,

            "average_order_value": aov,

            "delivered_orders": status_counts.get('DELIVERED', 0),

            "processing_orders": status_counts.get('PROCESSING', 0),

            "shipped_orders": status_counts.get('SHIPPED', 0),

            "cancelled_orders": status_counts.get('CANCELLED', 0),

            "currency": "INR"

        },

        "status_breakdown": status_counts,

        "daily_trend": daily_trend,

        "top_selling_products": top_prods_data

    }, status=200)





@csrf_exempt

def api_vendor_earnings_overview(request):

    """

    API: Get Vendor Earnings, Balance Summary & Recent Ledger

    Method: GET

    Endpoint: /api/vendor/earnings/overview/

    Header: Authorization: Bearer <vendor_token>

    """

    if request.method != "GET":

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    vendor, err_resp = _require_vendor_auth(request)

    if err_resp:

        return err_resp



    balance_summary = _get_vendor_balance_summary(vendor)

    recent_earnings = VendorEarning.objects.filter(vendor=vendor).order_by('-created_at')[:20]



    return JsonResponse({

        "success": True,

        "balance_summary": balance_summary,

        "recent_earnings": [e.to_dict() for e in recent_earnings]

    }, status=200)





# =============================================================================

# Withdrawal / Settlement REST APIs

# =============================================================================



@csrf_exempt

def api_vendor_payout_request(request):

    """

    API: Request Withdrawal Settlement to Registered Bank Account

    Method: POST

    Endpoint: /api/vendor/payout/request/

    Header: Authorization: Bearer <vendor_token>

    """

    if request.method != "POST":

        return JsonResponse({"success": False, "message": "Method not allowed. Use POST."}, status=405)



    vendor, err_resp = _require_vendor_auth(request)

    if err_resp:

        return err_resp



    data = _parse_request_data(request)

    raw_amount = data.get("amount")

    if raw_amount is None or str(raw_amount).strip() == "":

        return JsonResponse({"success": False, "message": "Field 'amount' is required."}, status=400)



    try:

        amount = float(raw_amount)

        if amount <= 0:

            return JsonResponse({"success": False, "message": "Withdrawal amount must be greater than zero."}, status=400)

    except (ValueError, TypeError):

        return JsonResponse({"success": False, "message": "Invalid amount value."}, status=400)



    bal_summary = _get_vendor_balance_summary(vendor)

    available_balance = bal_summary['available_balance']



    if amount > available_balance:

        return JsonResponse({

            "success": False,

            "message": f"Requested amount ₹{amount:.2f} exceeds your current available balance of ₹{available_balance:.2f}."

        }, status=400)



    bank_name = str(data.get("bank_name") or vendor.bank_name or "").strip()

    account_number = str(data.get("account_number") or vendor.account_number or "").strip()

    ifsc_code = str(data.get("ifsc_code") or vendor.ifsc_code or "").strip()

    notes = str(data.get("notes", "")).strip()



    if not bank_name or not account_number or not ifsc_code:

        return JsonResponse({

            "success": False,

            "message": "Bank details incomplete. Please provide 'bank_name', 'account_number', and 'ifsc_code' or update your store bank profile."

        }, status=400)



    payout = VendorPayout.objects.create(

        vendor=vendor,

        amount=amount,

        bank_name=bank_name,

        account_number=account_number,

        ifsc_code=ifsc_code,

        status='PENDING',

        admin_notes=notes

    )



    new_bal_summary = _get_vendor_balance_summary(vendor)



    return JsonResponse({

        "success": True,

        "message": f"Withdrawal request of ₹{amount:.2f} submitted successfully! Funds will be credited after compliance processing.",

        "payout": payout.to_dict(),

        "remaining_available_balance": new_bal_summary['available_balance']

    }, status=201)





@csrf_exempt

def api_vendor_payout_history(request):

    """

    API: List Withdrawal / Settlement History

    Method: GET

    Endpoint: /api/vendor/payout/history/

    Header: Authorization: Bearer <vendor_token>

    """

    if request.method != "GET":

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    vendor, err_resp = _require_vendor_auth(request)

    if err_resp:

        return err_resp



    qs = VendorPayout.objects.filter(vendor=vendor)

    status_param = request.GET.get('status', '').strip().upper()

    if status_param and status_param != 'ALL':

        qs = qs.filter(status=status_param)



    limit = 50

    if request.GET.get('limit'):

        try:

            limit = max(1, min(int(request.GET.get('limit')), 200))

        except (ValueError, TypeError):

            pass



    payouts = [p.to_dict() for p in qs[:limit]]



    return JsonResponse({

        "success": True,

        "count": len(payouts),

        "payouts": payouts

    }, status=200)





@csrf_exempt

def api_vendor_payout_detail(request, payout_id):

    """

    API: Get Specific Settlement Details

    Method: GET

    Endpoint: /api/vendor/payout/detail/<payout_id>/

    Header: Authorization: Bearer <vendor_token>

    """

    if request.method != "GET":

        return JsonResponse({"success": False, "message": "Method not allowed. Use GET."}, status=405)



    vendor, err_resp = _require_vendor_auth(request)

    if err_resp:

        return err_resp



    payout = None

    if str(payout_id).isdigit():

        payout = VendorPayout.objects.filter(id=int(payout_id)).first()

    if not payout:

        payout = VendorPayout.objects.filter(payout_number__iexact=str(payout_id).strip()).first()



    if not payout:

        return JsonResponse({"success": False, "message": f"Settlement '{payout_id}' not found."}, status=404)



    if payout.vendor_id != vendor.id:

        return JsonResponse({

            "success": False,

            "message": "Access denied. You do not have permission to view this settlement."

        }, status=403)



    return JsonResponse({

        "success": True,

        "payout": payout.to_dict()

    }, status=200)

