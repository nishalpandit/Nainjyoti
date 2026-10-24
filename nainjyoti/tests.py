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
    OrderItem,
    OrderRequest,
    PaymentTransaction,
    Product,
    ProductReview,
    ProductVariant,
    StockLog,
    UserAddress,
    UserProfile,
    VendorProfile,
    VendorPayout,
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

    def test_category_and_product_catalogue_are_public_and_random_feed_is_safe(self):
        hidden_product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Unapproved Hidden Product',
            sku='HIDDEN-UNAPPROVED-1',
            price='500.00',
            stock_quantity=5,
            status='ACTIVE',
            is_approved=False,
        )

        category_response = self.client.get(reverse('api_user_category_list'))
        search_response = self.client.get(reverse('api_user_product_search'))
        detail_response = self.client.get(reverse('api_user_product_detail', args=[self.product.id]))
        variants_response = self.client.get(reverse('api_user_product_variants', args=[self.variant_product.id]))
        random_response = self.client.get(reverse('api_user_random_products'), {'limit': 100})
        random_alias_response = self.client.get(reverse('api_random_products_alias'), {'limit': 1})

        for response in (
            category_response,
            search_response,
            detail_response,
            variants_response,
            random_response,
            random_alias_response,
        ):
            self.assertEqual(response.status_code, 200, response.content)

        random_body = random_response.json()
        returned_ids = {item['id'] for item in random_body['products']}
        self.assertTrue(random_body['randomized'])
        self.assertIn(self.product.id, returned_ids)
        self.assertIn(self.variant_product.id, returned_ids)
        self.assertNotIn(hidden_product.id, returned_ids)
        self.assertEqual(random_body['returned_count'], 2)
        self.assertIn('no-store', random_response['Cache-Control'])
        self.assertEqual(
            self.client.get(reverse('api_user_random_products'), {'limit': 101}).status_code,
            400,
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


class AdminDashboardCRUDTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='marketplace_staff',
            password='admin-pass',
            is_staff=True,
        )
        customer_user = User.objects.create_user(username='delete_customer')
        self.customer = UserProfile.objects.create(
            user=customer_user,
            first_name='Delete',
            last_name='Customer',
            phone='9555500001',
        )
        self.default_address = UserAddress.objects.create(
            user=self.customer,
            full_name='Delete Customer',
            phone='9555500001',
            address_line_1='First address',
            city='Delhi',
            state='Delhi',
            pincode='110001',
            is_default=True,
        )
        self.other_address = UserAddress.objects.create(
            user=self.customer,
            full_name='Delete Customer',
            phone='9555500001',
            address_line_1='Second address',
            city='Delhi',
            state='Delhi',
            pincode='110002',
        )
        vendor_user = User.objects.create_user(username='delete_vendor')
        self.vendor = VendorProfile.objects.create(
            user=vendor_user,
            business_name='Delete Vendor',
            owner_name='Vendor Owner',
            phone='9555500002',
            status='APPROVED',
        )
        self.category = Category.objects.create(name='Delete Category', status='ACTIVE')
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Delete Product',
            sku='ADMIN-DELETE-1',
            price='100.00',
            stock_quantity=2,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            customer_name=self.customer.full_name,
            customer_phone=self.customer.phone,
            shipping_address='First address',
            shipping_city='Delhi',
            shipping_state='Delhi',
            shipping_pincode='110001',
            total_amount='100.00',
        )
        self.payout = VendorPayout.objects.create(
            vendor=self.vendor,
            amount='50.00',
            bank_name='Test Bank',
            account_number='1234567890',
            ifsc_code='TEST0001234',
        )

    def test_custom_admin_and_admin_api_require_staff(self):
        dashboard_url = reverse('admin_dashboard')
        api_url = reverse('api_admin_product_list')
        self.assertEqual(self.client.get(dashboard_url).status_code, 302)
        self.assertEqual(self.client.get(api_url).status_code, 401)

        regular_user = User.objects.create_user(username='not_staff', password='user-pass')
        self.client.force_login(regular_user)
        self.assertEqual(self.client.get(dashboard_url).status_code, 302)
        self.assertEqual(self.client.get(api_url).status_code, 403)

        self.client.force_login(self.admin_user)
        self.assertEqual(self.client.get(dashboard_url).status_code, 200)
        self.assertEqual(self.client.get(api_url).status_code, 200)

    def test_staff_can_render_all_dynamic_crud_pages_and_django_editors(self):
        self.client.force_login(self.admin_user)
        page_names = [
            'admin_customers', 'admin_addresses', 'admin_vendors', 'admin_vendor_approval',
            'admin_categories', 'admin_products', 'admin_product_approval', 'admin_orders',
            'admin_payments', 'admin_commissions', 'admin_order_requests',
            'admin_notifications', 'admin_notification_add',
        ]
        for page_name in page_names:
            with self.subTest(page=page_name):
                self.assertEqual(self.client.get(reverse(page_name)).status_code, 200)

        add_pages = [
            'admin_vendor_add',
            'admin_product_add',
            'admin:nainjyoti_userprofile_add',
            'admin:nainjyoti_useraddress_add',
            'admin:nainjyoti_order_add',
            'admin:nainjyoti_vendorpayout_add',
        ]
        for page_name in add_pages:
            with self.subTest(page=page_name):
                self.assertEqual(self.client.get(reverse(page_name)).status_code, 200)

        self.assertContains(self.client.get(reverse('admin_product_add')), 'Add on behalf of vendor')

    def test_admin_can_edit_block_and_unblock_vendor_access(self):
        self.vendor.user.set_password('vendor-pass')
        self.vendor.user.save(update_fields=['password'])
        self.client.force_login(self.admin_user)

        edit_response = self.client.post(reverse('admin_vendor_edit', args=[self.vendor.id]), {
            'business_name': 'Updated Vendor Store',
            'owner_name': 'Updated Owner',
            'email': 'updated-vendor@example.com',
            'phone': '9555500099',
            'status': 'APPROVED',
            'business_type': 'Manufacturer',
            'category': 'Clothing',
        })
        self.assertRedirects(edit_response, reverse('admin_vendors'))
        self.vendor.refresh_from_db()
        self.vendor.user.refresh_from_db()
        self.assertEqual(self.vendor.business_name, 'Updated Vendor Store')
        self.assertEqual(self.vendor.user.email, 'updated-vendor@example.com')

        token = self.vendor.auth_token
        blocked = self.client.post(reverse('admin_vendor_toggle_block', args=[self.vendor.id]))
        self.assertRedirects(blocked, reverse('admin_vendors'))
        self.vendor.refresh_from_db()
        self.vendor.user.refresh_from_db()
        self.assertEqual(self.vendor.status, 'BLOCKED')
        self.assertFalse(self.vendor.user.is_active)

        api_response = self.client.get(
            reverse('api_vendor_profile'),
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertIn(api_response.status_code, (401, 403))

        unblocked = self.client.post(reverse('admin_vendor_toggle_block', args=[self.vendor.id]))
        self.assertRedirects(unblocked, reverse('admin_vendors'))
        self.vendor.refresh_from_db()
        self.vendor.user.refresh_from_db()
        self.assertEqual(self.vendor.status, 'APPROVED')
        self.assertTrue(self.vendor.user.is_active)

    def test_admin_product_form_creates_product_for_selected_vendor(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('admin_product_add'), {
            'vendor_id': str(self.vendor.id),
            'category_id': str(self.category.id),
            'name': 'Admin Created Shirt',
            'sku': 'ADMIN-SHIRT-001',
            'price': '999.00',
            'discount_price': '799.00',
            'stock_quantity': '12',
            'low_stock_threshold': '3',
            'unit': 'Piece',
            'description': 'Created by admin for the selected vendor.',
            'status': 'ACTIVE',
            'is_approved': 'on',
        })
        self.assertRedirects(response, reverse('admin_products'))
        created = Product.objects.get(sku='ADMIN-SHIRT-001')
        self.assertEqual(created.vendor, self.vendor)
        self.assertEqual(created.category, self.category)
        self.assertTrue(created.is_approved)
        self.assertEqual(created.stock_quantity, 12)
        self.assertTrue(StockLog.objects.filter(product=created, new_stock=12).exists())

    def test_admin_can_process_order_request_and_notify_customer(self):
        order_item = OrderItem.objects.create(
            order=self.order,
            vendor=self.vendor,
            product=self.product,
            product_name=self.product.name,
            product_sku=self.product.sku,
            price='100.00',
            quantity=1,
            total_price='100.00',
        )
        order_request = OrderRequest.objects.create(
            customer=self.customer,
            order=self.order,
            request_type='CANCEL',
            reason='Ordered by mistake',
        )
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('admin_order_request_update', args=[order_request.id]),
            {'status': 'COMPLETED', 'admin_notes': 'Cancellation completed by admin.'},
        )
        self.assertRedirects(response, reverse('admin_order_requests'))
        order_request.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(order_request.status, 'COMPLETED')
        self.assertEqual(self.order.status, 'CANCELLED')
        order_item.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order_item.status, 'CANCELLED')
        self.assertEqual(self.product.stock_quantity, 3)
        self.client.post(
            reverse('admin_order_request_update', args=[order_request.id]),
            {'status': 'COMPLETED', 'admin_notes': 'Repeated save must not restore stock twice.'},
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertEqual(
            StockLog.objects.filter(reference_id=f'CANCEL-{order_request.request_number}-{order_item.id}').count(),
            1,
        )
        self.assertTrue(Notification.objects.filter(
            user=self.customer,
            notification_type='CANCELLATION',
            data__request_id=order_request.id,
        ).exists())

    def test_admin_can_send_database_backed_customer_notification(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('admin_notification_add'), {
            'audience': 'ONE',
            'customer_id': str(self.customer.id),
            'notification_type': 'SYSTEM',
            'title': 'Account notice',
            'message': 'Your account information was updated.',
        })
        self.assertRedirects(response, reverse('admin_notifications'))
        notification = Notification.objects.get(user=self.customer, title='Account notice')
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.message, 'Your account information was updated.')

    def test_delete_endpoints_are_post_only_and_apply_model_delete_rules(self):
        self.client.force_login(self.admin_user)
        self.assertEqual(
            self.client.get(reverse('admin_category_delete', args=[self.category.id])).status_code,
            405,
        )

        self.client.post(reverse('admin_address_delete', args=[self.default_address.id]))
        self.other_address.refresh_from_db()
        self.assertTrue(self.other_address.is_default)

        self.client.post(reverse('admin_category_delete', args=[self.category.id]))
        self.product.refresh_from_db()
        self.assertIsNone(self.product.category_id)

        product_id = self.product.id
        self.client.post(reverse('admin_product_delete', args=[product_id]))
        self.assertFalse(Product.objects.filter(id=product_id).exists())

        order_id = self.order.id
        self.client.post(reverse('admin_order_delete', args=[order_id]))
        self.assertFalse(Order.objects.filter(id=order_id).exists())

        payout_id = self.payout.id
        self.client.post(reverse('admin_payout_delete', args=[payout_id]))
        self.assertFalse(VendorPayout.objects.filter(id=payout_id).exists())

        customer_id = self.customer.id
        customer_user_id = self.customer.user_id
        self.client.post(reverse('admin_customer_delete', args=[customer_id]))
        self.assertFalse(UserProfile.objects.filter(id=customer_id).exists())
        self.assertFalse(User.objects.filter(id=customer_user_id).exists())

        vendor_id = self.vendor.id
        vendor_user_id = self.vendor.user_id
        self.client.post(reverse('admin_vendor_delete', args=[vendor_id]))
        self.assertFalse(VendorProfile.objects.filter(id=vendor_id).exists())
        self.assertFalse(User.objects.filter(id=vendor_user_id).exists())
