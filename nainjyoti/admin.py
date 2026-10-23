from django.contrib import admin
from .models import (
    Category, VendorProfile, UserProfile, UserAddress, OTPRecord, Product, ProductVariant, CartItem, WishlistItem,
    ProductReview, StockLog, Order, PaymentTransaction, OrderItem, OrderRequest, Notification,
    OrderStatusHistory, VendorEarning, VendorPayout
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


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('title', 'product', 'sku', 'price', 'stock_quantity', 'is_active')
    list_filter = ('is_active', 'color', 'size')
    search_fields = ('title', 'sku', 'product__name')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'variant', 'quantity', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = (
        'user__first_name', 'user__last_name', 'user__phone',
        'product__name', 'product__sku', 'variant__title', 'variant__sku',
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'variant', 'created_at')
    list_filter = ('created_at', 'product__category')
    search_fields = (
        'user__first_name', 'user__last_name', 'user__phone',
        'product__name', 'product__sku', 'variant__title', 'variant__sku',
        'product__vendor__business_name',
    )
    readonly_fields = ('created_at',)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_verified_purchase', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_verified_purchase', 'is_approved', 'created_at')
    search_fields = ('product__name', 'user__first_name', 'user__last_name', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant', 'vendor', 'movement_type', 'quantity_changed', 'previous_stock', 'new_stock', 'reason', 'created_at')
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


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'address_type', 'city', 'state', 'pincode', 'is_default', 'created_at')
    list_filter = ('address_type', 'is_default', 'state', 'country')
    search_fields = ('full_name', 'phone', 'address_line_1', 'city', 'state', 'pincode', 'user__phone')


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
    list_display = ('id', 'order', 'vendor', 'product_name', 'variant_title', 'price', 'quantity', 'total_price', 'status', 'courier_name', 'tracking_number')
    list_filter = ('status', 'vendor', 'created_at')
    search_fields = ('order__order_number', 'product_name', 'product_sku', 'variant_title', 'variant__sku', 'vendor__business_name', 'tracking_number')
    ordering = ('-created_at',)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'order', 'customer', 'method', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('method', 'status', 'currency', 'created_at')
    search_fields = (
        'reference', 'order__order_number', 'customer__phone',
        'provider_order_id', 'provider_payment_id',
    )
    readonly_fields = ('reference', 'created_at', 'updated_at')


@admin.register(OrderRequest)
class OrderRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'request_type', 'order', 'order_item', 'customer', 'status', 'created_at')
    list_filter = ('request_type', 'status', 'created_at')
    search_fields = ('request_number', 'order__order_number', 'customer__phone', 'reason', 'details')
    readonly_fields = ('request_number', 'created_at', 'updated_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'order', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__first_name', 'user__last_name', 'user__phone')
    readonly_fields = ('created_at', 'read_at')


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


