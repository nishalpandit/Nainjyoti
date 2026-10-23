import hashlib
import hmac
import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    CartItem,
    Category,
    Notification,
    Order,
    OrderRequest,
    PaymentTransaction,
    Product,
    ProductReview,
    ProductVariant,
    StockLog,
    UserAddress,
    UserProfile,
    VendorProfile,
)


class CustomerCommerceAPITests(TestCase):
    def setUp(self):
        customer_user = User.objects.create_user(username='commerce_customer')
        self.customer = UserProfile.objects.create(
            user=customer_user,
            first_name='Ananya',
            last_name='Iyer',
            phone='9666600001',
            email='commerce@example.com',
        )
        other_user = User.objects.create_user(username='other_commerce_customer')
        self.other_customer = UserProfile.objects.create(
            user=other_user,
            first_name='Other',
            last_name='Customer',
            phone='9666600002',
        )
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {self.customer.auth_token}'}
        self.other_auth = {'HTTP_AUTHORIZATION': f'Bearer {self.other_customer.auth_token}'}
        self.address = UserAddress.objects.create(
            user=self.customer,
            full_name='Ananya Iyer',
            phone='9666600001',
            address_line_1='12 MG Road',
            city='Bengaluru',
            state='Karnataka',
            pincode='560001',
            country='India',
            is_default=True,
        )
        vendor_user = User.objects.create_user(username='commerce_vendor')
        self.vendor = VendorProfile.objects.create(
            user=vendor_user,
            business_name='Commerce Store',
            owner_name='Vendor Owner',
            phone='9666600003',
            status='APPROVED',
        )
        self.category = Category.objects.create(name='Commerce Category', status='ACTIVE')
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Simple Checkout Product',
            sku='CHECKOUT-SIMPLE-1',
            price='1000.00',
            discount_price='800.00',
            stock_quantity=10,
            status='ACTIVE',
            is_approved=True,
        )
        self.variant_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Variant Checkout Product',
            sku='CHECKOUT-VARIANT-1',
            price='2000.00',
            stock_quantity=1,
            status='ACTIVE',
            is_approved=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.variant_product,
            title='Black / Large',
            color='Black',
            size='L',
            sku='CHECKOUT-VARIANT-BLK-L',
            price='1800.00',
            discount_price='1500.00',
            stock_quantity=5,
            is_active=True,
        )

    def post_json(self, url, payload, headers=None):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            **(self.auth if headers is None else headers),
        )

    def add_cart_rows(self):
        CartItem.objects.create(user=self.customer, product=self.product, quantity=2)
        CartItem.objects.create(
            user=self.customer,
            product=self.variant_product,
            variant=self.variant,
            quantity=1,
        )

    def checkout(self, payment_method='COD'):
        return self.post_json(
            reverse('api_user_checkout'),
            {'address_id': self.address.id, 'payment_method': payment_method},
        )

    def test_cod_checkout_creates_order_deducts_stock_and_clears_cart(self):
        self.add_cart_rows()
        response = self.checkout('COD')

        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body['order']['total_amount'], 3100.0)
        self.assertEqual(body['order']['payment_method'], 'COD')
        self.assertFalse(body['payment']['requires_online_payment'])
        self.assertTrue(body['cart_cleared'])
        self.assertFalse(CartItem.objects.filter(user=self.customer).exists())
        self.product.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)
        self.assertEqual(self.variant.stock_quantity, 4)
        self.assertEqual(StockLog.objects.filter(movement_type='SALE').count(), 2)
        self.assertEqual(Notification.objects.filter(user=self.customer).count(), 1)

    def test_checkout_validation_rolls_back_everything(self):
        CartItem.objects.create(user=self.customer, product=self.product, quantity=11)
        response = self.checkout('COD')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(PaymentTransaction.objects.count(), 0)
        self.assertEqual(CartItem.objects.filter(user=self.customer).count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    @override_settings(PAYMENT_WEBHOOK_SECRET='test-payment-secret')
    def test_online_checkout_payment_status_and_signed_verification(self):
        CartItem.objects.create(user=self.customer, product=self.product, quantity=1)
        checkout = self.checkout('ONLINE')
        self.assertEqual(checkout.status_code, 201, checkout.content)
        payment = checkout.json()['payment']
        self.assertEqual(payment['status'], 'INITIATED')
        self.assertTrue(payment['requires_online_payment'])

        status_response = self.client.get(
            reverse('api_user_payment_status', args=[payment['reference']]),
            **self.auth,
        )
        self.assertEqual(status_response.status_code, 200)

        provider = 'TEST_GATEWAY'
        provider_order_id = 'gateway_order_1'
        provider_payment_id = 'gateway_payment_1'
        signed_payload = '|'.join([
            payment['reference'], 'PAID', provider, provider_order_id, provider_payment_id,
        ])
        signature = hmac.new(
            b'test-payment-secret',
            signed_payload.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        verified = self.client.post(
            reverse('api_user_payment_verify'),
            data=json.dumps({
                'payment_reference': payment['reference'],
                'status': 'PAID',
                'provider': provider,
                'provider_order_id': provider_order_id,
                'provider_payment_id': provider_payment_id,
            }),
            content_type='application/json',
            HTTP_X_PAYMENT_SIGNATURE=signature,
            **self.auth,
        )
        self.assertEqual(verified.status_code, 200, verified.content)
        self.assertEqual(verified.json()['payment']['status'], 'PAID')

    def test_order_history_detail_and_tracking_are_customer_scoped(self):
        self.add_cart_rows()
        checkout = self.checkout('COD').json()
        order_id = checkout['order']['id']

        history = self.client.get(reverse('api_user_orders_list'), **self.auth)
        detail = self.client.get(reverse('api_user_order_detail', args=[order_id]), **self.auth)
        tracking = self.client.get(reverse('api_user_order_tracking', args=[order_id]), **self.auth)
        forbidden = self.client.get(reverse('api_user_order_detail', args=[order_id]), **self.other_auth)

        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()['count'], 1)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(tracking.status_code, 200)
        self.assertEqual(len(tracking.json()['items']), 2)
        self.assertEqual(forbidden.status_code, 404)

    def test_cancel_and_return_requests_validate_order_state(self):
        CartItem.objects.create(user=self.customer, product=self.product, quantity=1)
        order_id = self.checkout('COD').json()['order']['id']
        cancel = self.post_json(
            reverse('api_user_order_request_create', args=[order_id]),
            {'request_type': 'CANCEL', 'reason': 'Ordered by mistake'},
        )
        duplicate = self.post_json(
            reverse('api_user_order_request_create', args=[order_id]),
            {'request_type': 'CANCEL', 'reason': 'Still want to cancel'},
        )
        early_return = self.post_json(
            reverse('api_user_order_request_create', args=[order_id]),
            {'request_type': 'RETURN', 'reason': 'Not needed'},
        )

        self.assertEqual(cancel.status_code, 201, cancel.content)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(early_return.status_code, 400)
        self.assertEqual(OrderRequest.objects.count(), 1)
        listing = self.client.get(reverse('api_user_order_request_list'), **self.auth)
        self.assertEqual(listing.json()['total_count'], 1)

        order = Order.objects.get(pk=order_id)
        order.status = 'DELIVERED'
        order.save(update_fields=['status', 'updated_at'])
        order_item = order.items.first()
        order_item.status = 'DELIVERED'
        order_item.save(update_fields=['status', 'updated_at'])
        returned = self.post_json(
            reverse('api_user_order_request_create', args=[order_id]),
            {
                'request_type': 'RETURN',
                'order_item_id': order_item.id,
                'reason': 'Item arrived damaged',
            },
        )
        self.assertEqual(returned.status_code, 201, returned.content)

    def test_review_create_list_update_delete(self):
        created = self.post_json(
            reverse('api_product_reviews', args=[self.product.id]),
            {'rating': 4, 'title': 'Good product', 'comment': 'Works as expected.'},
        )
        self.assertEqual(created.status_code, 201, created.content)
        review_id = created.json()['review']['id']
        self.assertFalse(created.json()['review']['is_verified_purchase'])

        listing = self.client.get(reverse('api_product_reviews', args=[self.product.id]))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()['average_rating'], 4.0)
        updated = self.post_json(
            reverse('api_user_review_update', args=[review_id]),
            {'rating': 5, 'comment': 'Even better after more use.'},
        )
        self.assertEqual(updated.json()['review']['rating'], 5)
        forbidden = self.post_json(
            reverse('api_user_review_update', args=[review_id]),
            {'rating': 1},
            headers=self.other_auth,
        )
        self.assertEqual(forbidden.status_code, 404)
        deleted = self.client.delete(reverse('api_user_review_delete', args=[review_id]), **self.auth)
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(ProductReview.objects.exists())

    def test_notification_list_count_and_read_controls(self):
        notification = Notification.objects.create(
            user=self.customer,
            notification_type='SYSTEM',
            title='Welcome',
            message='Welcome to Nainjyoti.',
        )
        listing = self.client.get(reverse('api_user_notifications_list'), **self.auth)
        count = self.client.get(reverse('api_user_notifications_unread_count'), **self.auth)
        marked = self.client.post(
            reverse('api_user_notification_mark_read', args=[notification.id]),
            **self.auth,
        )
        all_read = self.client.post(reverse('api_user_notifications_mark_all_read'), **self.auth)

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()['total_count'], 1)
        self.assertEqual(count.json()['unread_count'], 1)
        self.assertTrue(marked.json()['notification']['is_read'])
        self.assertEqual(all_read.json()['unread_count'], 0)

