"""
Integration Tests for ADAKEV ISP Billing System
Tests the complete customer journey: Registration → Login → Dashboard → Invoice → Payment
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date
from customers.models import Customer
from services.models import ServicePlan
from billing.models import CustomerService, Invoice, Payment


class CustomerJourneyIntegrationTest(TestCase):
    """Complete integration test for customer journey"""

    def setUp(self):
        """Set up test client and initial data"""
        self.client = Client()
        
        # Create a service plan
        self.plan = ServicePlan.objects.create(
            name='Premium Internet',
            price=2500.00,
            speed_mbps=50
        )

    def test_complete_customer_journey(self):
        """Test the complete customer journey from registration to payment"""
        
        # Step 1: Customer Registration
        print("\n✓ Step 1: Testing Customer Registration...")
        registration_data = {
            'username': 'johndoe',
            'first_name': 'John',
            'last_name': 'Doe',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'phone_number': '254712345678',
            'address': '123 Main Street, Nairobi',
            'id_number': '12345678'
        }
        
        response = self.client.post(reverse('customers:customer_register'), registration_data)
        
        # Should redirect to dashboard after successful registration
        self.assertEqual(response.status_code, 302)
        
        # Verify user was created
        user = User.objects.get(username='johndoe')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        
        # Verify customer profile was created
        customer = Customer.objects.get(user=user)
        self.assertEqual(customer.phone_number, '254712345678')
        print("  ✓ Customer registration successful")

        # Step 2: Customer Login
        print("\n✓ Step 2: Testing Customer Login...")
        self.client.logout()
        
        login_response = self.client.post(reverse('customers:customer_login'), {
            'username': 'johndoe',
            'password': 'SecurePass123!'
        }, follow=False)
        
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response['Location'], reverse('customers:customer_dashboard'))
        print("  ✓ Customer login successful")

        # Step 3: View Dashboard
        print("\n✓ Step 3: Testing Customer Dashboard...")
        self.client.login(username='johndoe', password='SecurePass123!')
        
        dashboard_response = self.client.get(reverse('customers:customer_dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertTemplateUsed(dashboard_response, 'customers/dashboard.html')
        self.assertContains(dashboard_response, 'John Doe')
        print("  ✓ Dashboard accessible and displays customer info")

        # Step 4: Create a subscription and invoice
        print("\n✓ Step 4: Setting up Subscription and Invoice...")
        subscription = CustomerService.objects.create(
            customer=customer,
            plan=self.plan,
            status='ACTIVE',
            start_date=date.today()
        )
        
        invoice = Invoice.objects.create(
            customer_service=subscription,
            amount=2500.00,
            due_date=date.today()
        )
        
        self.assertEqual(invoice.status, 'PENDING')
        self.assertEqual(invoice.amount, 2500.00)
        print("  ✓ Subscription and invoice created")

        # Step 5: View Invoices List
        print("\n✓ Step 5: Testing Invoices List View...")
        invoices_response = self.client.get(reverse('customers:customer_invoices'))
        self.assertEqual(invoices_response.status_code, 200)
        self.assertTemplateUsed(invoices_response, 'customers/invoices.html')
        self.assertContains(invoices_response, str(invoice.id))
        print("  ✓ Invoices list accessible")

        # Step 6: View Invoice Details
        print("\n✓ Step 6: Testing Invoice Detail View...")
        invoice_detail_response = self.client.get(
            reverse('customers:customer_invoice_detail', args=[invoice.id])
        )
        self.assertEqual(invoice_detail_response.status_code, 200)
        self.assertTemplateUsed(invoice_detail_response, 'customers/invoice_detail.html')
        self.assertContains(invoice_detail_response, f'Invoice #{invoice.id}')
        self.assertContains(invoice_detail_response, '2500.00')
        print("  ✓ Invoice details accessible")

        # Step 7: Initiate M-Pesa Payment
        print("\n✓ Step 7: Testing M-Pesa Payment Initiation...")
        payment_page_response = self.client.get(
            reverse('billing:initiate_mpesa_payment', args=[invoice.id])
        )
        self.assertEqual(payment_page_response.status_code, 200)
        self.assertTemplateUsed(payment_page_response, 'billing/mpesa_payment.html')
        self.assertContains(payment_page_response, 'M-Pesa')
        print("  ✓ M-Pesa payment page accessible")

        # Step 8: Submit Payment Form
        print("\n✓ Step 8: Testing Payment Form Submission...")
        payment_data = {
            'phone_number': '254712345678'
        }
        
        payment_response = self.client.post(
            reverse('billing:initiate_mpesa_payment', args=[invoice.id]),
            payment_data,
            follow=True
        )
        
        # Should redirect back to invoice or dashboard after submission
        self.assertIn(payment_response.status_code, [200, 302])
        print("  ✓ Payment form submitted successfully")

        # Step 9: Verify Payment Status
        print("\n✓ Step 9: Testing Payment Status Update...")
        updated_invoice = Invoice.objects.get(id=invoice.id)
        # After payment submission, invoice should be marked as PAID
        self.assertEqual(updated_invoice.status, 'PAID')
        self.assertEqual(updated_invoice.amount, 2500.00)
        print("  ✓ Invoice status updated to PAID after payment")

        # Step 10: Test Logout
        print("\n✓ Step 10: Testing Logout...")
        logout_response = self.client.get(reverse('customers:customer_logout'))
        self.assertEqual(logout_response.status_code, 302)
        
        # Try to access dashboard - should redirect to login
        dashboard_after_logout = self.client.get(reverse('customers:customer_dashboard'))
        self.assertEqual(dashboard_after_logout.status_code, 302)
        print("  ✓ Logout successful, protected routes require login")

        print("\n" + "="*60)
        print("✅ COMPLETE CUSTOMER JOURNEY TEST PASSED!")
        print("="*60)
        print("\nAll steps verified:")
        print("  1. Registration ✓")
        print("  2. Login ✓")
        print("  3. Dashboard ✓")
        print("  4. Subscription & Invoice ✓")
        print("  5. Invoices List ✓")
        print("  6. Invoice Details ✓")
        print("  7. M-Pesa Payment Page ✓")
        print("  8. Payment Form ✓")
        print("  9. Payment Status ✓")
        print("  10. Logout ✓")
        print("="*60 + "\n")


class CustomerPaymentFlowIntegrationTest(TestCase):
    """Test the payment flow with actual payment recording"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create user and customer
        self.user = User.objects.create_user(
            username='testcustomer',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Customer'
        )
        
        self.customer = Customer.objects.create(
            user=self.user,
            phone_number='254712345678',
            address='Test Street',
            id_number='87654321'
        )
        
        # Create service plan and subscription
        self.plan = ServicePlan.objects.create(
            name='Basic Internet',
            price=1500.00,
            speed_mbps=10
        )
        
        self.subscription = CustomerService.objects.create(
            customer=self.customer,
            plan=self.plan,
            status='ACTIVE',
            start_date=date.today()
        )
        
        # Create invoice
        self.invoice = Invoice.objects.create(
            customer_service=self.subscription,
            amount=1500.00,
            due_date=date.today()
        )

    def test_payment_recording_and_verification(self):
        """Test recording and verifying payments"""
        
        print("\n✓ Testing Payment Recording and Verification...")
        
        # Verify initial invoice status
        self.assertEqual(self.invoice.status, 'PENDING')
        self.assertEqual(self.invoice.amount, 1500.00)
        print("  ✓ Initial invoice status: PENDING")

        # Record a payment
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount_paid=1500.00,
            mpesa_code='ABC123DEF456'
        )
        
        self.assertEqual(payment.amount_paid, 1500.00)
        self.assertEqual(payment.mpesa_code, 'ABC123DEF456')
        print("  ✓ Payment recorded successfully")
        print(f"    - Amount: KSh {payment.amount_paid}")
        print(f"    - M-Pesa Code: {payment.mpesa_code}")

        # Verify payment appears in invoice payments
        invoice_payments = self.invoice.payment_set.all()
        self.assertEqual(invoice_payments.count(), 1)
        self.assertEqual(invoice_payments.first().mpesa_code, 'ABC123DEF456')
        print("  ✓ Payment linked to invoice")

        # Login and verify payment appears in dashboard
        self.client.login(username='testcustomer', password='testpass123')
        dashboard_response = self.client.get(reverse('customers:customer_dashboard'))
        
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'ABC123DEF456')
        print("  ✓ Payment visible in customer dashboard")

        print("\n✅ PAYMENT FLOW TEST PASSED!\n")
