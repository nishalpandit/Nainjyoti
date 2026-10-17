from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import secrets
from datetime import timedelta

class VendorProfile(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    vendor_code = models.CharField(max_length=20, unique=True, blank=True)
    business_name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    business_type = models.CharField(max_length=100, default='Retailer')
    category = models.CharField(max_length=100, default='General Merchandise')

    # Tax & Identification
    gst_number = models.CharField(max_length=30, blank=True)
    pan_number = models.CharField(max_length=20, blank=True)

    # Bank Settlement Details
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)

    # Address Details
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)

    # Uploaded Documents
    gst_document = models.FileField(upload_to='vendor_documents/gst/', blank=True, null=True)
    pan_document = models.FileField(upload_to='vendor_documents/pan/', blank=True, null=True)
    id_proof = models.FileField(upload_to='vendor_documents/id_proof/', blank=True, null=True)

    # Store Branding & Description
    store_description = models.TextField(blank=True)
    store_logo = models.ImageField(upload_to='vendor_documents/logos/', blank=True, null=True)
    store_banner = models.ImageField(upload_to='vendor_documents/banners/', blank=True, null=True)
    support_email = models.EmailField(blank=True, null=True)

    # Verification Lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    rejection_reason = models.TextField(blank=True)
    auth_token = models.CharField(max_length=64, unique=True, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business_name} ({self.vendor_code}) - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.vendor_code:
            self.vendor_code = f"VEND-{random.randint(10000, 99999)}"
        if not self.auth_token:
            self.auth_token = secrets.token_hex(32)
        super().save(*args, **kwargs)

    @property
    def logo_url(self):
        if self.store_logo and hasattr(self.store_logo, 'url'):
            return self.store_logo.url
        return None

    @property
    def banner_url(self):
        if self.store_banner and hasattr(self.store_banner, 'url'):
            return self.store_banner.url
        return None

    def generate_new_token(self):
        self.auth_token = secrets.token_hex(32)
        self.save(update_fields=['auth_token'])
        return self.auth_token

    def to_dict(self):
        return {
            'id': self.id,
            'vendor_code': self.vendor_code,
            'business_name': self.business_name,
            'owner_name': self.owner_name,
            'email': self.user.email if self.user else '',
            'support_email': self.support_email or '',
            'phone': self.phone,
            'business_type': self.business_type,
            'category': self.category,
            'store_description': self.store_description,
            'store_logo': self.logo_url,
            'store_banner': self.banner_url,
            'status': self.status,
            'status_display': self.get_status_display(),
            'rejection_reason': self.rejection_reason if self.status == 'REJECTED' else '',
            'gst_number': self.gst_number,
            'pan_number': self.pan_number,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'ifsc_code': self.ifsc_code,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'gst_document': self.gst_document.url if self.gst_document and hasattr(self.gst_document, 'url') else None,
            'pan_document': self.pan_document.url if self.pan_document and hasattr(self.pan_document, 'url') else None,
            'id_proof': self.id_proof.url if self.id_proof and hasattr(self.id_proof, 'url') else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class UserProfile(models.Model):
    """
    Consumer / App Customer Profile for Mobile App and Web
    Authentication is via Phone Number + OTP
    """
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
        ('Prefer not to say', 'Prefer not to say'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    email = models.EmailField(blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=30, choices=GENDER_CHOICES, default='Prefer not to say')
    profile_photo = models.ImageField(upload_to='user_profiles/photos/', blank=True, null=True)
    auth_token = models.CharField(max_length=64, unique=True, blank=True, null=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"

    def save(self, *args, **kwargs):
        if not self.auth_token:
            self.auth_token = secrets.token_hex(32)
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def photo_url(self):
        if self.profile_photo and hasattr(self.profile_photo, 'url'):
            return self.profile_photo.url
        return None

    def generate_new_token(self):
        self.auth_token = secrets.token_hex(32)
        self.save(update_fields=['auth_token'])
        return self.auth_token

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'email': self.email or '',
            'dob': self.dob.strftime('%Y-%m-%d') if self.dob else None,
            'gender': self.gender,
            'profile_photo': self.photo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OTPRecord(models.Model):
    """
    Stores OTP verification codes for Phone login & registration
    """
    PURPOSE_CHOICES = [
        ('LOGIN', 'Login'),
        ('REGISTER', 'Register'),
    ]

    phone = models.CharField(max_length=20, db_index=True)
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='LOGIN')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP {self.otp_code} for {self.phone} ({self.purpose})"

    def is_valid(self):
        return not self.is_verified and self.expires_at > timezone.now()

    @classmethod
    def generate_for_phone(cls, phone, purpose='LOGIN', expiry_minutes=10):
        # Invalidate previous unverified OTPs for this phone and purpose
        cls.objects.filter(phone=phone, purpose=purpose, is_verified=False).delete()
        
        # Generate 6-digit OTP
        code = str(random.randint(100000, 999999))
        expires = timezone.now() + timedelta(minutes=expiry_minutes)
        return cls.objects.create(
            phone=phone,
            otp_code=code,
            purpose=purpose,
            expires_at=expires
        )
