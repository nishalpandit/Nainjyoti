import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from nainjyoti.models import (
    CartItem,
    Category,
    Product,
    ProductVariant,
    UserProfile,
    VendorProfile,
)


class AddToCartAPITests(TestCase):
    def setUp(self):
        customer_user = User.objects.create_user(username='cart_customer')
        self.customer = UserProfile.objects.create(
            user=customer_user,
            first_name='Ananya',
            last_name='Iyer',
            phone='9888800001',
        )
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {self.customer.auth_token}'}

        vendor_user = User.objects.create_user(username='cart_vendor')
        self.vendor = VendorProfile.objects.create(
            user=vendor_user,
            business_name='Cart Test Store',
            owner_name='Test Vendor',
            phone='9888800002',
            status='APPROVED',
        )
        self.category = Category.objects.create(name='Cart Test Category', status='ACTIVE')
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Simple Product',
            sku='CART-SIMPLE-001',
            price='1000.00',
            discount_price='800.00',
            stock_quantity=5,
            status='ACTIVE',
            is_approved=True,
        )
        self.variant_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Variant Product',
            sku='CART-VARIANT-001',
            price='1500.00',
            stock_quantity=1,
            status='ACTIVE',
            is_approved=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.variant_product,
            title='Blue / Large',
            color='Blue',
            size='L',
            sku='CART-VARIANT-BLUE-L',
            price='1400.00',
            discount_price='1200.00',
            stock_quantity=3,
            is_active=True,
        )

    def add(self, payload, authenticated=True):
        headers = self.auth if authenticated else {}
        return self.client.post(
            reverse('api_user_cart_add'),
            data=json.dumps(payload),
            content_type='application/json',
            **headers,
        )

    def test_authentication_is_required(self):
        response = self.add({'product_id': self.product.id}, authenticated=False)
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()['success'])

    def test_add_product_persists_and_returns_totals(self):
        response = self.add({'product_id': self.product.id, 'quantity': 2})

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertTrue(body['success'])
        self.assertEqual(body['cart_item']['quantity'], 2)
        self.assertEqual(body['cart_item']['effective_price'], 800.0)
        self.assertEqual(body['cart_item']['line_total'], 1600.0)
        self.assertEqual(body['cart']['item_count'], 1)
        self.assertEqual(body['cart']['total_quantity'], 2)
        self.assertEqual(body['cart']['regular_subtotal'], 2000.0)
        self.assertEqual(body['cart']['discount'], 400.0)
        self.assertEqual(body['cart']['total'], 1600.0)
        saved = CartItem.objects.get(user=self.customer, product=self.product)
        self.assertEqual(saved.quantity, 2)
        self.assertIsNone(saved.variant)

    def test_adding_same_item_increments_existing_cart_line(self):
        first = self.add({'product_id': self.product.id, 'quantity': 1})
        second = self.add({'product_id': self.product.id, 'quantity': 2})

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(second.json()['cart_item']['quantity'], 3)
        self.assertEqual(CartItem.objects.filter(user=self.customer).count(), 1)

    def test_variant_is_required_and_saved_for_variant_product(self):
        missing_variant = self.add({'product_id': self.variant_product.id})
        self.assertEqual(missing_variant.status_code, 400)
        self.assertIn('variant_id is required', missing_variant.json()['message'])

        response = self.add({
            'product_id': self.variant_product.id,
            'variant_id': self.variant.id,
            'quantity': 2,
        })
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['cart_item']['variant_id'], self.variant.id)
        self.assertEqual(response.json()['cart_item']['effective_price'], 1200.0)
        self.assertEqual(
            CartItem.objects.get(user=self.customer, product=self.variant_product).variant,
            self.variant,
        )

    def test_stock_limit_includes_quantity_already_in_cart(self):
        self.add({'product_id': self.product.id, 'quantity': 4})
        response = self.add({'product_id': self.product.id, 'quantity': 2})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['available_stock'], 5)
        self.assertEqual(response.json()['quantity_already_in_cart'], 4)
        self.assertEqual(CartItem.objects.get(user=self.customer).quantity, 4)

    def test_unavailable_product_and_invalid_values_are_rejected(self):
        bad_quantity = self.add({'product_id': self.product.id, 'quantity': 0})
        self.assertEqual(bad_quantity.status_code, 400)

        self.vendor.status = 'PENDING'
        self.vendor.save(update_fields=['status'])
        unavailable = self.add({'product_id': self.product.id})
        self.assertEqual(unavailable.status_code, 400)
        self.assertEqual(CartItem.objects.count(), 0)

