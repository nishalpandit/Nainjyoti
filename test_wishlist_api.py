import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from nainjyoti.models import (
    Category,
    Product,
    ProductVariant,
    UserProfile,
    VendorProfile,
    WishlistItem,
)


class WishlistAPITests(TestCase):
    def setUp(self):
        customer_user = User.objects.create_user(username='wishlist_customer')
        self.customer = UserProfile.objects.create(
            user=customer_user,
            first_name='Ananya',
            last_name='Iyer',
            phone='9777700001',
        )
        other_user = User.objects.create_user(username='wishlist_other_customer')
        self.other_customer = UserProfile.objects.create(
            user=other_user,
            first_name='Other',
            last_name='Customer',
            phone='9777700002',
        )
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {self.customer.auth_token}'}
        self.other_auth = {'HTTP_AUTHORIZATION': f'Bearer {self.other_customer.auth_token}'}

        vendor_user = User.objects.create_user(username='wishlist_vendor')
        self.vendor = VendorProfile.objects.create(
            user=vendor_user,
            business_name='Wishlist Test Store',
            owner_name='Wishlist Vendor',
            phone='9777700003',
            status='APPROVED',
        )
        self.category = Category.objects.create(name='Wishlist Test Category', status='ACTIVE')
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Wishlist Product',
            sku='WISH-PRODUCT-001',
            description='A product used in wishlist tests.',
            price='1000.00',
            discount_price='850.00',
            stock_quantity=6,
            status='ACTIVE',
            is_approved=True,
        )
        self.variant_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Wishlist Variant Product',
            sku='WISH-VARIANT-001',
            price='1600.00',
            stock_quantity=1,
            status='ACTIVE',
            is_approved=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.variant_product,
            title='Black / Large',
            color='Black',
            size='L',
            sku='WISH-VARIANT-BLK-L',
            price='1500.00',
            discount_price='1250.00',
            stock_quantity=4,
            is_active=True,
        )

    def add(self, product_id, variant_id=None, headers=None):
        payload = {'product_id': product_id}
        if variant_id is not None:
            payload['variant_id'] = variant_id
        return self.client.post(
            reverse('api_user_wishlist_add'),
            data=json.dumps(payload),
            content_type='application/json',
            **(self.auth if headers is None else headers),
        )

    def test_authentication_is_required(self):
        add_response = self.add(self.product.id, headers={})
        list_response = self.client.get(reverse('api_user_wishlist_list'))

        self.assertEqual(add_response.status_code, 401)
        self.assertEqual(list_response.status_code, 401)
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_add_persists_product_and_duplicate_is_idempotent(self):
        created = self.add(self.product.id)
        duplicate = self.add(self.product.id)

        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.json()['wishlist_item']['effective_price'], 850.0)
        self.assertFalse(created.json()['already_exists'])
        self.assertEqual(duplicate.status_code, 200, duplicate.content)
        self.assertTrue(duplicate.json()['already_exists'])
        self.assertEqual(WishlistItem.objects.filter(user=self.customer).count(), 1)

    def test_list_is_customer_specific_and_contains_variant_summary(self):
        WishlistItem.objects.create(user=self.other_customer, product=self.product)
        self.add(self.variant_product.id, self.variant.id)

        response = self.client.get(reverse('api_user_wishlist_list'), **self.auth)

        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['total_items'], 1)
        item = body['wishlist'][0]
        self.assertEqual(item['product_id'], self.variant_product.id)
        self.assertEqual(item['variant_id'], self.variant.id)
        self.assertEqual(item['color'], 'Black')
        self.assertEqual(item['size'], 'L')
        self.assertTrue(item['has_variants'])
        self.assertEqual(item['variant_count'], 1)
        self.assertEqual(item['effective_price'], 1250.0)

    def test_variant_is_required_and_each_variant_is_saved_separately(self):
        missing_variant = self.add(self.variant_product.id)
        self.assertEqual(missing_variant.status_code, 400)
        self.assertIn('variant_id is required', missing_variant.json()['message'])

        blue_variant = ProductVariant.objects.create(
            product=self.variant_product,
            title='Blue / Large',
            color='Blue',
            size='L',
            sku='WISH-VARIANT-BLU-L',
            price='1500.00',
            discount_price='1300.00',
            stock_quantity=2,
            is_active=True,
        )
        black = self.add(self.variant_product.id, self.variant.id)
        blue = self.add(self.variant_product.id, blue_variant.id)

        self.assertEqual(black.status_code, 201, black.content)
        self.assertEqual(blue.status_code, 201, blue.content)
        self.assertEqual(black.json()['wishlist_item']['color'], 'Black')
        self.assertEqual(blue.json()['wishlist_item']['color'], 'Blue')
        self.assertEqual(
            WishlistItem.objects.filter(user=self.customer, product=self.variant_product).count(),
            2,
        )

        removed = self.client.delete(
            reverse(
                'api_user_wishlist_remove_variant',
                args=[self.variant_product.id, self.variant.id],
            ),
            **self.auth,
        )
        self.assertEqual(removed.status_code, 200, removed.content)
        self.assertFalse(
            WishlistItem.objects.filter(user=self.customer, variant=self.variant).exists()
        )
        self.assertTrue(
            WishlistItem.objects.filter(user=self.customer, variant=blue_variant).exists()
        )

    def test_remove_deletes_only_authenticated_customer_item(self):
        own_item = WishlistItem.objects.create(user=self.customer, product=self.product)
        WishlistItem.objects.create(user=self.other_customer, product=self.product)

        response = self.client.delete(
            reverse('api_user_wishlist_remove', args=[self.product.id]),
            **self.auth,
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['removed_wishlist_item_id'], own_item.id)
        self.assertFalse(WishlistItem.objects.filter(user=self.customer).exists())
        self.assertTrue(WishlistItem.objects.filter(user=self.other_customer).exists())

    def test_remove_missing_item_returns_404(self):
        response = self.client.delete(
            reverse('api_user_wishlist_remove', args=[self.product.id]),
            **self.auth,
        )
        self.assertEqual(response.status_code, 404)

    def test_unavailable_and_invalid_products_are_rejected(self):
        invalid = self.client.post(
            reverse('api_user_wishlist_add'),
            data=json.dumps({'product_id': 'invalid'}),
            content_type='application/json',
            **self.auth,
        )
        self.assertEqual(invalid.status_code, 400)

        self.vendor.status = 'PENDING'
        self.vendor.save(update_fields=['status'])
        unavailable = self.add(self.product.id)
        self.assertEqual(unavailable.status_code, 400)
        self.assertEqual(WishlistItem.objects.count(), 0)
