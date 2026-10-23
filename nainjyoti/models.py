from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import secrets
from datetime import timedelta
from django.utils.text import slugify

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

    @property
    def initials(self):
        name = self.owner_name or self.business_name or "Seller"
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        return name[:2].upper()

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
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserAddress(models.Model):
    """Saved delivery address owned by a customer profile."""

    ADDRESS_TYPE_CHOICES = [
        ('Home', 'Home'),
        ('Work', 'Work'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=20, choices=ADDRESS_TYPE_CHOICES, default='Home')
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    landmark = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')
    is_default = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_default=True),
                name='unique_default_address_per_user',
            ),
        ]
        verbose_name = 'User Address'
        verbose_name_plural = 'User Addresses'

    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.state} ({self.pincode})"

    def to_dict(self):
        return {
            'id': self.id,
            'address_type': self.address_type,
            'full_name': self.full_name,
            'phone': self.phone,
            'address_line_1': self.address_line_1,
            'address_line_2': self.address_line_2,
            'landmark': self.landmark,
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'country': self.country,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
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


class Category(models.Model):
    """
    Master Category Taxonomy.
    Includes name, description, image thumbnail, and active status for product listings.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='categories/images/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return f"{self.name} ({self.status})"

    @property
    def image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return None

    @property
    def products_count(self):
        return self.products.filter(status='ACTIVE', is_approved=True, vendor__status='APPROVED').count()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'image_url': self.image_url,
            'status': self.status,
            'products_count': self.products_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Product(models.Model):
    """
    Product Model for Vendor / Merchant Catalog.
    Includes item details, pricing, stock, category master mapping, and product image.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('OUT_OF_STOCK', 'Out of Stock'),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    unit = models.CharField(max_length=30, default='Piece', blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.name} ({self.sku}) - ₹{self.price}"

    def save(self, *args, **kwargs):
        if not self.sku:
            unique_sku = f"PROD-{random.randint(100000, 999999)}"
            while Product.objects.filter(sku=unique_sku).exists():
                unique_sku = f"PROD-{random.randint(100000, 999999)}"
            self.sku = unique_sku
        # Sync product active/out-of-stock status with inventory
        if self.stock_quantity <= 0:
            self.status = 'OUT_OF_STOCK'
        elif self.status == 'OUT_OF_STOCK' and self.stock_quantity > 0:
            self.status = 'ACTIVE'
        super().save(*args, **kwargs)

    @property
    def image_url(self):
        if self.image:
            if hasattr(self.image, 'url'):
                try:
                    return self.image.url
                except Exception:
                    pass
            img_str = str(self.image).strip()
            if img_str.startswith('http://') or img_str.startswith('https://') or img_str.startswith('/media/'):
                return img_str
            return f"/media/{img_str}"
        return None

    @property
    def stock_status(self):
        if self.stock_quantity <= 0:
            return 'OUT_OF_STOCK'
        elif self.stock_quantity <= self.low_stock_threshold:
            return 'LOW_STOCK'
        return 'HEALTHY'

    @property
    def has_variants(self):
        return self.variants.exists()

    @property
    def active_variant_count(self):
        return self.variants.filter(is_active=True).count()

    @property
    def variant_count(self):
        return self.active_variant_count

    @property
    def customer_effective_price(self):
        variants = list(self.variants.filter(is_active=True))
        if variants:
            return min(variant.effective_price for variant in variants)
        return float(self.discount_price if self.discount_price is not None else self.price)

    def sync_variant_inventory(self, force=False):
        """Keep legacy product stock/status fields aligned with variant inventory."""
        if not self.pk:
            return
        variants = self.variants.filter(is_active=True)
        if not force and not self.variants.exists():
            return
        total_stock = sum(max(variant.stock_quantity, 0) for variant in variants)
        status = self.status
        if total_stock <= 0 and status != 'INACTIVE':
            status = 'OUT_OF_STOCK'
        elif total_stock > 0 and status == 'OUT_OF_STOCK':
            status = 'ACTIVE'
        Product.objects.filter(pk=self.pk).update(
            stock_quantity=total_stock,
            status=status,
            updated_at=timezone.now(),
        )
        self.stock_quantity = total_stock
        self.status = status

    @property
    def stock_valuation(self):
        variants = list(self.variants.filter(is_active=True))
        if variants:
            return round(sum(variant.effective_price * max(variant.stock_quantity, 0) for variant in variants), 2)
        return round(self.customer_effective_price * max(self.stock_quantity, 0), 2)

    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.business_name if self.vendor else None,
            'vendor_code': self.vendor.vendor_code if self.vendor else None,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'name': self.name,
            'sku': self.sku,
            'description': self.description,
            'price': float(self.price) if self.price is not None else 0.0,
            'discount_price': float(self.discount_price) if self.discount_price is not None else None,
            'effective_price': self.customer_effective_price,
            'stock_quantity': self.stock_quantity,
            'low_stock_threshold': self.low_stock_threshold,
            'stock_status': self.stock_status,
            'stock_valuation': self.stock_valuation,
            'unit': self.unit,
            'image': self.image_url,
            'status': self.status,
            'is_approved': self.is_approved,
            'has_variants': self.has_variants,
            'variant_count': self.active_variant_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProductVariant(models.Model):
    """Purchasable color, size, or material option belonging to a product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    title = models.CharField(max_length=150)
    color = models.CharField(max_length=50, blank=True, default='')
    size = models.CharField(max_length=50, blank=True, default='')
    material = models.CharField(max_length=100, blank=True, default='')
    sku = models.CharField(max_length=60, unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.IntegerField(default=0)
    image = models.ImageField(upload_to='products/variants/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'

    def __str__(self):
        return f"{self.product.name} - {self.title} ({self.sku})"

    def save(self, *args, **kwargs):
        if not self.sku:
            base_sku = self.product.sku or f"PRD-{self.product.id}"
            suffix = f"-{self.size}" if self.size else ""
            if self.color:
                suffix += f"-{self.color[:3].upper()}"
            sku_prefix = f"{base_sku}{suffix}"[:56]
            generated_sku = f"{sku_prefix}-{random.randint(100, 999)}"
            while ProductVariant.objects.filter(sku=generated_sku).exists():
                generated_sku = f"{sku_prefix}-{random.randint(100, 999)}"
            self.sku = generated_sku
        super().save(*args, **kwargs)
        self.product.sync_variant_inventory()

    def delete(self, *args, **kwargs):
        product = self.product
        result = super().delete(*args, **kwargs)
        product.sync_variant_inventory(force=True)
        return result

    @property
    def image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return self.product.image_url

    @property
    def effective_price(self):
        if self.discount_price is not None:
            return float(self.discount_price)
        if self.price is not None:
            return float(self.price)
        product_price = (
            self.product.discount_price
            if self.product.discount_price is not None
            else self.product.price
        )
        return float(product_price)

    def to_dict(self):
        regular_price = float(self.price) if self.price is not None else float(self.product.price)
        sale_price = float(self.discount_price) if self.discount_price is not None else (
            float(self.product.discount_price) if self.product.discount_price is not None else None
        )
        return {
            'id': self.id,
            'product_id': self.product.id,
            'title': self.title,
            'color': self.color,
            'size': self.size,
            'material': self.material,
            'sku': self.sku,
            'price': regular_price,
            'discount_price': sale_price,
            'effective_price': self.effective_price,
            'stock_quantity': self.stock_quantity,
            'in_stock': self.stock_quantity > 0,
            'image_url': self.image_url,
            'is_active': self.is_active,
        }


class CartItem(models.Model):
    """A customer's persisted cart line for a product or product variant."""

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart_items',
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                condition=models.Q(variant__isnull=True),
                name='unique_product_cart_item_without_variant',
            ),
            models.UniqueConstraint(
                fields=['user', 'product', 'variant'],
                condition=models.Q(variant__isnull=False),
                name='unique_product_variant_cart_item',
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='cart_item_quantity_at_least_one',
            ),
        ]

    def __str__(self):
        item_name = self.variant.title if self.variant else self.product.name
        return f"{self.user.full_name} - {item_name} x {self.quantity}"

    @property
    def regular_unit_price(self):
        if self.variant and self.variant.price is not None:
            return self.variant.price
        return self.product.price

    @property
    def effective_unit_price(self):
        if self.variant:
            if self.variant.discount_price is not None:
                return self.variant.discount_price
            if self.variant.price is not None:
                return self.variant.price
        if self.product.discount_price is not None:
            return self.product.discount_price
        return self.product.price

    @property
    def available_stock(self):
        return self.variant.stock_quantity if self.variant else self.product.stock_quantity

    @property
    def line_total(self):
        return self.effective_unit_price * self.quantity

    @property
    def line_savings(self):
        return (self.regular_unit_price - self.effective_unit_price) * self.quantity

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name,
            'product_sku': self.product.sku,
            'variant_id': self.variant_id,
            'variant_title': self.variant.title if self.variant else None,
            'variant_sku': self.variant.sku if self.variant else None,
            'color': self.variant.color if self.variant else '',
            'size': self.variant.size if self.variant else '',
            'material': self.variant.material if self.variant else '',
            'image_url': self.variant.image_url if self.variant else self.product.image_url,
            'regular_price': float(self.regular_unit_price),
            'effective_price': float(self.effective_unit_price),
            'quantity': self.quantity,
            'line_total': float(self.line_total),
            'savings': float(self.line_savings),
            'available_stock': self.available_stock,
            'in_stock': self.available_stock > 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class WishlistItem(models.Model):
    """A product or exact product variant saved by a customer for later."""

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='wishlist_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                condition=models.Q(variant__isnull=True),
                name='unique_product_wishlist_item_without_variant',
            ),
            models.UniqueConstraint(
                fields=['user', 'product', 'variant'],
                condition=models.Q(variant__isnull=False),
                name='unique_product_variant_wishlist_item',
            ),
        ]

    def __str__(self):
        item_name = self.variant.title if self.variant else self.product.name
        return f"{self.user.full_name} - {item_name}"

    @property
    def regular_price(self):
        if self.variant and self.variant.price is not None:
            return self.variant.price
        return self.product.price

    @property
    def effective_price(self):
        if self.variant:
            if self.variant.discount_price is not None:
                return self.variant.discount_price
            if self.variant.price is not None:
                return self.variant.price
        if self.product.discount_price is not None:
            return self.product.discount_price
        return self.product.price

    @property
    def available_stock(self):
        return self.variant.stock_quantity if self.variant else self.product.stock_quantity

    @property
    def is_available(self):
        product = self.product
        return (
            product.status == 'ACTIVE'
            and product.is_approved
            and product.vendor.status == 'APPROVED'
            and (product.category is None or product.category.status == 'ACTIVE')
            and (self.variant is None or self.variant.is_active)
        )

    def to_dict(self):
        product = self.product
        return {
            'id': self.id,
            'product_id': product.id,
            'name': product.name,
            'sku': product.sku,
            'variant_id': self.variant_id,
            'variant_title': self.variant.title if self.variant else None,
            'variant_sku': self.variant.sku if self.variant else None,
            'color': self.variant.color if self.variant else '',
            'size': self.variant.size if self.variant else '',
            'material': self.variant.material if self.variant else '',
            'description': product.description,
            'price': float(self.regular_price),
            'discount_price': (
                float(self.effective_price)
                if self.effective_price != self.regular_price else None
            ),
            'effective_price': float(self.effective_price),
            'image_url': self.variant.image_url if self.variant else product.image_url,
            'category_id': product.category_id,
            'category_name': product.category.name if product.category else None,
            'vendor_id': product.vendor_id,
            'vendor_name': product.vendor.business_name,
            'stock_quantity': self.available_stock,
            'in_stock': self.available_stock > 0,
            'has_variants': product.has_variants,
            'variant_count': product.active_variant_count,
            'is_available': self.is_available,
            'added_at': self.created_at.isoformat() if self.created_at else None,
        }


class StockLog(models.Model):
    """
    Inventory / Stock Audit Ledger.
    Records every single addition, deduction, or recount with timestamps and reasons.
    """
    MOVEMENT_CHOICES = [
        ('RESTOCK', 'Restock / Purchase'),
        ('SALE', 'Customer Order Sale'),
        ('RETURN', 'Customer Return'),
        ('DAMAGE', 'Damaged / Expired / Lost'),
        ('CORRECTION', 'Physical Inventory Correction'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_logs')
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_logs',
    )
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='stock_logs')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_CHOICES, default='RESTOCK')
    quantity_changed = models.IntegerField()  # Positive for addition, negative for deduction
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True, default='')
    reference_id = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Movement Log'
        verbose_name_plural = 'Stock Movement Logs'

    def __str__(self):
        sign = "+" if self.quantity_changed > 0 else ""
        return f"{self.product.name} ({sign}{self.quantity_changed}) - {self.get_movement_type_display()} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else '',
            'sku': self.product.sku if self.product else '',
            'variant_id': self.variant_id,
            'variant_title': self.variant.title if self.variant else None,
            'variant_sku': self.variant.sku if self.variant else None,
            'vendor_id': self.vendor_id,
            'movement_type': self.movement_type,
            'movement_type_display': self.get_movement_type_display(),
            'quantity_changed': self.quantity_changed,
            'previous_stock': self.previous_stock,
            'new_stock': self.new_stock,
            'reason': self.reason,
            'reference_id': self.reference_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Order(models.Model):
    """
    Master Order model for customer purchases.
    Can contain items from one or multiple vendors.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('ONLINE', 'Online Payment'),
        ('PREPAID', 'Prepaid Online'),
        ('UPI', 'UPI Payment'),
        ('CARD', 'Credit / Debit Card'),
        ('NETBANKING', 'Net Banking'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    order_number = models.CharField(max_length=50, unique=True, blank=True, db_index=True)
    customer = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True, null=True)

    # Shipping details
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=20)

    # Financial & Status
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default='COD')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"{self.order_number} - {self.customer_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.order_number:
            import random
            today_str = timezone.now().strftime('%Y%m%d')
            unique_ord = f"ORD-{today_str}-{random.randint(1000, 9999)}"
            while Order.objects.filter(order_number=unique_ord).exists():
                unique_ord = f"ORD-{today_str}-{random.randint(1000, 9999)}"
            self.order_number = unique_ord
        super().save(*args, **kwargs)

    def to_dict(self, vendor=None):
        """
        Serializes order data. If vendor is provided, filters items strictly to that vendor.
        """
        items_qs = self.items.all().select_related('product', 'variant', 'vendor')
        if vendor:
            items_qs = items_qs.filter(vendor=vendor)

        items_list = [item.to_dict() for item in items_qs]
        vendor_subtotal = sum(item['total_price'] for item in items_list) if vendor else float(self.total_amount)
        payment_transaction = getattr(self, 'payment_transaction', None)

        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email or '',
            'shipping_address': self.shipping_address,
            'shipping_city': self.shipping_city,
            'shipping_state': self.shipping_state,
            'shipping_pincode': self.shipping_pincode,
            'total_amount': float(self.total_amount),
            'vendor_subtotal': round(vendor_subtotal, 2) if vendor else float(self.total_amount),
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'payment': payment_transaction.to_dict() if payment_transaction else None,
            'status': self.status,
            'status_display': self.get_status_display(),
            'item_count': len(items_list),
            'items': items_list,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentTransaction(models.Model):
    """Gateway-neutral payment record created for every customer checkout."""

    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment_transaction',
    )
    customer = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_transactions',
    )
    reference = models.CharField(max_length=64, unique=True, db_index=True, blank=True)
    method = models.CharField(max_length=20, choices=[('COD', 'Cash on Delivery'), ('ONLINE', 'Online Payment')])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    provider = models.CharField(max_length=50, blank=True, default='')
    provider_order_id = models.CharField(max_length=120, blank=True, default='')
    provider_payment_id = models.CharField(max_length=120, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'

    def __str__(self):
        return f"{self.reference} - {self.order.order_number} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.reference:
            reference = f"PAY-{timezone.now().strftime('%Y%m%d')}-{secrets.token_hex(5).upper()}"
            while PaymentTransaction.objects.filter(reference=reference).exists():
                reference = f"PAY-{timezone.now().strftime('%Y%m%d')}-{secrets.token_hex(5).upper()}"
            self.reference = reference
        super().save(*args, **kwargs)

    @property
    def requires_online_payment(self):
        return self.method == 'ONLINE' and self.status not in ['PAID', 'REFUNDED']

    def to_dict(self):
        return {
            'id': self.id,
            'reference': self.reference,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else None,
            'method': self.method,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'requires_online_payment': self.requires_online_payment,
            'provider': self.provider or None,
            'provider_order_id': self.provider_order_id or None,
            'provider_payment_id': self.provider_payment_id or None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class OrderItem(models.Model):
    """
    Individual items inside an order, bound to the specific vendor who sells the product.
    """
    STATUS_CHOICES = Order.STATUS_CHOICES

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='order_items', db_index=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
    )
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=60, blank=True)
    variant_title = models.CharField(max_length=150, blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Fulfillment & Tracking
    courier_name = models.CharField(max_length=100, blank=True, default='')
    tracking_number = models.CharField(max_length=100, blank=True, default='')
    dispatch_date = models.DateTimeField(null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity} ({self.order.order_number}) - Vendor: {self.vendor.business_name}"

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.price * self.quantity
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else '',
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.business_name if self.vendor else '',
            'product_id': self.product_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'variant_id': self.variant_id,
            'variant_title': self.variant_title,
            'variant': self.variant.to_dict() if self.variant else None,
            'price': float(self.price),
            'quantity': self.quantity,
            'total_price': float(self.total_price),
            'status': self.status,
            'status_display': self.get_status_display(),
            'courier_name': self.courier_name,
            'tracking_number': self.tracking_number,
            'dispatch_date': self.dispatch_date.isoformat() if self.dispatch_date else None,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OrderStatusHistory(models.Model):
    """
    Audit log of status updates for an order or specific order item.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, null=True, blank=True, related_name='status_history')
    vendor = models.ForeignKey(VendorProfile, on_delete=models.SET_NULL, null=True, blank=True)
    old_status = models.CharField(max_length=30, blank=True, default='')
    new_status = models.CharField(max_length=30)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status Histories'

    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} -> {self.new_status} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'order_item_id': self.order_item_id,
            'vendor_id': self.vendor_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class VendorEarning(models.Model):
    """
    Vendor Earnings Ledger.
    Tracks gross order revenue, platform commission, net earnings, and clearance state.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Clearance'),
        ('AVAILABLE', 'Available for Withdrawal'),
        ('WITHDRAWN', 'Withdrawn / Settled'),
        ('REFUNDED', 'Refunded / Reversal'),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='earnings', db_index=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='earnings')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, null=True, blank=True, related_name='earnings')

    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)  # e.g. 5% platform fee
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)  # gross - commission

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    cleared_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vendor Earning'
        verbose_name_plural = 'Vendor Earnings'

    def __str__(self):
        return f"₹{self.net_amount} for {self.vendor.business_name} (Order {self.order.order_number}) - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.commission_amount:
            self.commission_amount = round(self.gross_amount * (self.commission_rate / 100), 2)
        if not self.net_amount:
            self.net_amount = self.gross_amount - self.commission_amount
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'order_id': self.order_id,
            'order_number': self.order.order_number if self.order else '',
            'order_item_id': self.order_item_id,
            'gross_amount': float(self.gross_amount),
            'commission_rate': float(self.commission_rate),
            'commission_amount': float(self.commission_amount),
            'net_amount': float(self.net_amount),
            'status': self.status,
            'status_display': self.get_status_display(),
            'cleared_at': self.cleared_at.isoformat() if self.cleared_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class VendorPayout(models.Model):
    """
    Settlement / Withdrawal Request for Vendor bank transfers.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('PROCESSING', 'Processing Bank Transfer'),
        ('COMPLETED', 'Completed / Settled'),
        ('REJECTED', 'Rejected'),
    ]

    payout_number = models.CharField(max_length=50, unique=True, blank=True, db_index=True)
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='payouts', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Destination Bank Account Details
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    utr_number = models.CharField(max_length=100, blank=True, default='')  # Unique Transaction Reference from bank
    admin_notes = models.TextField(blank=True, default='')

    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Vendor Payout / Settlement'
        verbose_name_plural = 'Vendor Payouts / Settlements'

    def __str__(self):
        return f"{self.payout_number} - ₹{self.amount} ({self.vendor.business_name}) - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.payout_number:
            import random
            today_str = timezone.now().strftime('%Y%m%d')
            self.payout_number = f"PAY-{today_str}-{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'payout_number': self.payout_number,
            'vendor_id': self.vendor_id,
            'vendor_name': self.vendor.business_name if self.vendor else '',
            'amount': float(self.amount),
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'ifsc_code': self.ifsc_code,
            'status': self.status,
            'status_display': self.get_status_display(),
            'utr_number': self.utr_number,
            'admin_notes': self.admin_notes,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
        }
