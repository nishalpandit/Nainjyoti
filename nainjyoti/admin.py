from django.contrib import admin
from .models import Category, VendorProfile, UserProfile, OTPRecord, Product, StockLog

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'vendor', 'category', 'price', 'discount_price', 'stock_quantity', 'low_stock_threshold', 'stock_status', 'status', 'is_approved', 'created_at')
    list_filter = ('status', 'is_approved', 'category', 'vendor')
    search_fields = ('name', 'sku', 'vendor__business_name', 'vendor__vendor_code', 'category__name')
    ordering = ('-created_at',)

@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ('product', 'vendor', 'movement_type', 'quantity_changed', 'previous_stock', 'new_stock', 'reason', 'created_at')
    list_filter = ('movement_type', 'created_at', 'vendor')
    search_fields = ('product__name', 'product__sku', 'vendor__business_name', 'reason', 'reference_id')
    ordering = ('-created_at',)


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

