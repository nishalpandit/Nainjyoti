import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import UserAddress, UserProfile


class AddressManagementAPITests(TestCase):
    def setUp(self):
        auth_user = User.objects.create_user(
            username='usr_9000000001',
            email='address.user@example.com',
            first_name='Ananya',
            last_name='Iyer',
        )
        self.profile = UserProfile.objects.create(
            user=auth_user,
            first_name='Ananya',
            last_name='Iyer',
            phone='9000000001',
            email='address.user@example.com',
            gender='Female',
        )
        other_user = User.objects.create_user(username='usr_9000000002')
        self.other_profile = UserProfile.objects.create(
            user=other_user,
            first_name='Other',
            last_name='Customer',
            phone='9000000002',
        )
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {self.profile.auth_token}'}
        self.valid_payload = {
            'address_type': 'Home',
            'full_name': 'Ananya Iyer',
            'phone': '9000000001',
            'address_line_1': '12, MG Road',
            'address_line_2': 'Apartment 4B',
            'landmark': 'Near Metro Station',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'pincode': '560001',
            'country': 'India',
        }

    def post_json(self, url, payload, **headers):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            **headers,
        )

    def create_address(self, **overrides):
        payload = {**self.valid_payload, **overrides}
        response = self.post_json(reverse('api_user_address_create'), payload, **self.auth)
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()['address']

    def test_create_requires_authentication_and_validates_input(self):
        unauthorized = self.post_json(reverse('api_user_address_create'), self.valid_payload)
        self.assertEqual(unauthorized.status_code, 401)

        invalid = self.post_json(
            reverse('api_user_address_create'),
            {**self.valid_payload, 'pincode': '5600'},
            **self.auth,
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('pincode', invalid.json()['errors'])
        self.assertEqual(UserAddress.objects.count(), 0)

    def test_create_persists_first_address_as_default(self):
        address_data = self.create_address()
        saved = UserAddress.objects.get(pk=address_data['id'])

        self.assertEqual(saved.user, self.profile)
        self.assertEqual(saved.city, 'Bengaluru')
        self.assertTrue(saved.is_default)
        self.assertTrue(address_data['is_default'])

    def test_list_detail_update_and_ownership(self):
        first = self.create_address()

        listing = self.client.get(reverse('api_user_address_list'), **self.auth)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()['count'], 1)
        self.assertEqual(listing.json()['default_address_id'], first['id'])

        detail = self.client.get(
            reverse('api_user_address_detail', args=[first['id']]),
            **self.auth,
        )
        self.assertEqual(detail.status_code, 200)

        updated = self.post_json(
            reverse('api_user_address_update', args=[first['id']]),
            {'address_type': 'Work', 'landmark': 'Opposite City Library'},
            **self.auth,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['address']['address_type'], 'Work')

        other_auth = {'HTTP_AUTHORIZATION': f'Bearer {self.other_profile.auth_token}'}
        forbidden_detail = self.client.get(
            reverse('api_user_address_detail', args=[first['id']]),
            **other_auth,
        )
        self.assertEqual(forbidden_detail.status_code, 404)

    def test_set_default_and_delete_promotes_remaining_address(self):
        first = self.create_address()
        second = self.create_address(
            address_type='Work',
            address_line_1='44, Residency Road',
            landmark='',
        )
        self.assertFalse(second['is_default'])

        default_response = self.client.post(
            reverse('api_user_address_set_default', args=[second['id']]),
            **self.auth,
        )
        self.assertEqual(default_response.status_code, 200)
        self.assertTrue(default_response.json()['address']['is_default'])
        self.assertFalse(UserAddress.objects.get(pk=first['id']).is_default)

        deleted = self.client.delete(
            reverse('api_user_address_delete', args=[second['id']]),
            **self.auth,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()['deleted_address_id'], second['id'])
        self.assertTrue(UserAddress.objects.get(pk=first['id']).is_default)

    def test_blocked_user_receives_forbidden(self):
        self.profile.is_active = False
        self.profile.save(update_fields=['is_active'])

        response = self.client.get(reverse('api_user_address_list'), **self.auth)
        self.assertEqual(response.status_code, 403)

    def test_admin_views_show_live_address_data(self):
        self.create_address()

        directory = self.client.get(reverse('admin_addresses'))
        self.assertEqual(directory.status_code, 200)
        self.assertContains(directory, '12, MG Road')
        self.assertContains(directory, 'Ananya Iyer')

        customer_detail = self.client.get(
            reverse('admin_customer_detail', args=[self.profile.id])
        )
        self.assertEqual(customer_detail.status_code, 200)
        self.assertEqual(customer_detail.json()['customer']['saved_address_count'], 1)
        self.assertEqual(customer_detail.json()['customer']['addresses'][0]['city'], 'Bengaluru')
