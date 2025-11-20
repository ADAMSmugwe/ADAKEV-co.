from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Customer

class CustomerModelTest(TestCase):
    """Test cases for Customer model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone_number='254712345678',
            address='123 Test Street',
            id_number='12345678'
        )

    def test_customer_creation(self):
        """Test customer model creation"""
        self.assertEqual(self.customer.user.username, 'testuser')
        self.assertEqual(self.customer.phone_number, '254712345678')
        self.assertEqual(str(self.customer), 'Test User - 254712345678')

    def test_customer_str_method(self):
        """Test customer string representation"""
        expected = 'Test User - 254712345678'
        self.assertEqual(str(self.customer), expected)

class CustomerViewsTest(TestCase):
    """Test cases for customer views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone_number='254712345678',
            address='123 Test Street',
            id_number='12345678'
        )

    def test_customer_login_view(self):
        """Test customer login view"""
        # Test GET request
        response = self.client.get(reverse('customers:customer_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'customers/login.html')

        # Test successful login
        response = self.client.post(reverse('customers:customer_login'), {
            'username': 'testuser',
            'password': 'testpass123'
        }, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('customers:customer_dashboard'))

    def test_customer_dashboard_authenticated(self):
        """Test customer dashboard for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('customers:customer_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'customers/dashboard.html')
        self.assertContains(response, 'Test User')

    def test_customer_dashboard_unauthenticated(self):
        """Test customer dashboard for unauthenticated user"""
        response = self.client.get(reverse('customers:customer_dashboard'))
        self.assertRedirects(response, f"{reverse('customers:customer_login')}?next={reverse('customers:customer_dashboard')}")

class CustomerAPITest(APITestCase):
    """Test cases for customer API"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone_number='254712345678',
            address='123 Test Street',
            id_number='12345678'
        )

    def test_api_customer_profile_authenticated(self):
        """Test API customer profile for authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('customers:api_customer_profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], '254712345678')

    def test_api_customer_profile_unauthenticated(self):
        """Test API customer profile for unauthenticated user"""
        response = self.client.get(reverse('customers:api_customer_profile'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
