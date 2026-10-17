from django.contrib import admin
from .models import Category, VendorProfile, UserProfile, OTPRecord

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ('vendor_code', 'business_name', 'owner_name', 'phone', 'category', 'status', 'created_at')
    list_filter = ('status', 'business_type', 'category')
    search_fields = ('vendor_code', 'business_name', 'owner_name', 'phone', 'gst_number')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'gender', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone', 'email')

@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ('phone', 'otp_code', 'purpose', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('purpose', 'is_verified')
    search_fields = ('phone', 'otp_code')
