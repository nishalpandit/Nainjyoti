from django.contrib import admin
from .models import (
    Category, VendorProfile, UserProfile, OTPRecord, Product, StockLog,
    Order, OrderItem, OrderStatusHistory, VendorEarning, VendorPayout
)

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


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'customer_phone', 'total_amount', 'payment_method', 'payment_status', 'status', 'created_at')
    list_filter = ('status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'customer_name', 'customer_phone', 'customer_email', 'shipping_address')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'vendor', 'product_name', 'price', 'quantity', 'total_price', 'status', 'courier_name', 'tracking_number')
    list_filter = ('status', 'vendor', 'created_at')
    search_fields = ('order__order_number', 'product_name', 'product_sku', 'vendor__business_name', 'tracking_number')
    ordering = ('-created_at',)


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'order_item', 'vendor', 'old_status', 'new_status', 'created_at')
    list_filter = ('new_status', 'created_at')
    search_fields = ('order__order_number', 'notes')
    ordering = ('-created_at',)


@admin.register(VendorEarning)
class VendorEarningAdmin(admin.ModelAdmin):
    list_display = ('id', 'vendor', 'order', 'gross_amount', 'commission_rate', 'commission_amount', 'net_amount', 'status', 'created_at')
    list_filter = ('status', 'vendor', 'created_at')
    search_fields = ('vendor__business_name', 'order__order_number')
    ordering = ('-created_at',)


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ('payout_number', 'vendor', 'amount', 'bank_name', 'account_number', 'ifsc_code', 'status', 'utr_number', 'requested_at', 'processed_at')
    list_filter = ('status', 'vendor', 'requested_at')
    search_fields = ('payout_number', 'vendor__business_name', 'account_number', 'utr_number')
    ordering = ('-requested_at',)


