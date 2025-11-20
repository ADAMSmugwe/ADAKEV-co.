from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date
from customers.models import Customer
from services.models import ServicePlan
from .models import CustomerService, Invoice, Payment

class BillingModelTest(TestCase):
    """Test cases for billing models"""

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
        self.plan = ServicePlan.objects.create(
            name='Test Plan',
            price=1000.00,
            speed_mbps=10
        )
        self.subscription = CustomerService.objects.create(
            customer=self.customer,
            plan=self.plan,
            status='ACTIVE',
            start_date=date.today()
        )
        self.invoice = Invoice.objects.create(
            customer_service=self.subscription,
            amount=1000.00,
            due_date=date.today()
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice,
            amount_paid=1000.00,
            mpesa_code='MPESA123456'
        )

    def test_invoice_creation(self):
        """Test invoice model creation"""
        self.assertEqual(self.invoice.amount, 1000.00)
        self.assertEqual(self.invoice.status, 'PENDING')
        self.assertEqual(str(self.invoice), f"Invoice #{self.invoice.id} - {self.customer.user.get_full_name()} (PENDING)")

    def test_payment_creation(self):
        """Test payment model creation"""
        self.assertEqual(self.payment.amount_paid, 1000.00)
        self.assertEqual(self.payment.mpesa_code, 'MPESA123456')
        self.assertEqual(str(self.payment), f"Payment #{self.payment.id} - MPESA123456")

    def test_customer_service_creation(self):
        """Test customer service model creation"""
        self.assertEqual(self.subscription.status, 'ACTIVE')
        expected_str = f"{self.customer} - {self.plan} (ACTIVE)"
        self.assertEqual(str(self.subscription), expected_str)

class BillingAPITest(APITestCase):
    """Test cases for billing API"""

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
        self.plan = ServicePlan.objects.create(
            name='Test Plan',
            price=1000.00,
            speed_mbps=10
        )
        self.subscription = CustomerService.objects.create(
            customer=self.customer,
            plan=self.plan,
            status='ACTIVE',
            start_date=date.today()
        )
        self.invoice = Invoice.objects.create(
            customer_service=self.subscription,
            amount=1000.00,
            due_date=date.today()
        )

    def test_api_customer_invoices_authenticated(self):
        """Test API customer invoices for authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('billing:api_customer_invoices'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['amount'], '1000.00')

    def test_api_customer_invoices_unauthenticated(self):
        """Test API customer invoices for unauthenticated user"""
        response = self.client.get(reverse('billing:api_customer_invoices'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_customer_payments_authenticated(self):
        """Test API customer payments for authenticated user"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('billing:api_customer_payments'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return empty list since no payments yet
        self.assertEqual(len(response.data), 0)
