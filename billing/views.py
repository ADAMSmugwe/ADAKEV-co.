from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import requests
from datetime import datetime
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import Invoice, Payment, CustomerService
from .serializers import InvoiceSerializer, PaymentSerializer, CustomerServiceSerializer
from customers.models import Customer

# Existing views...

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_customer_invoices(request):
    """API endpoint for customer's invoices"""
    try:
        customer = Customer.objects.get(user=request.user)
        subscriptions = customer.customerservice_set.all()
        invoices = []

        for subscription in subscriptions:
            invoices.extend(subscription.invoice_set.all().order_by('-created_at'))

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer profile not found'}, status=404)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_customer_payments(request):
    """API endpoint for customer's payment history"""
    try:
        customer = Customer.objects.get(user=request.user)
        subscriptions = customer.customerservice_set.all()
        payments = []

        for subscription in subscriptions:
            for invoice in subscription.invoice_set.all():
                payments.extend(invoice.payment_set.all().order_by('-timestamp'))

        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer profile not found'}, status=404)

class InvoiceListAPIView(generics.ListAPIView):
    """API view for listing invoices"""
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        customer = get_object_or_404(Customer, user=self.request.user)
        subscriptions = customer.customerservice_set.all()
        invoices = []
        for subscription in subscriptions:
            invoices.extend(subscription.invoice_set.all())
        return invoices

class InvoiceDetailAPIView(generics.RetrieveAPIView):
    """API view for invoice details"""
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        customer = get_object_or_404(Customer, user=self.request.user)
        subscriptions = customer.customerservice_set.all()
        invoice_ids = []
        for subscription in subscriptions:
            invoice_ids.extend(subscription.invoice_set.values_list('id', flat=True))
        return Invoice.objects.filter(id__in=invoice_ids)

@login_required
def initiate_mpesa_payment(request, invoice_id):
    """Initiate M-Pesa STK Push payment for an invoice"""
    try:
        customer = Customer.objects.get(user=request.user)
        invoice = Invoice.objects.get(
            id=invoice_id,
            customer_service__customer=customer,
            status='PENDING'
        )
    except (Customer.DoesNotExist, Invoice.DoesNotExist):
        messages.error(request, 'Invoice not found or access denied.')
        return redirect('customers:customer_invoices')

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')

        # Validate phone number (should be in format 254XXXXXXXXX)
        if not phone_number or not phone_number.startswith('254') or len(phone_number) != 12:
            messages.error(request, 'Please enter a valid M-Pesa phone number (254XXXXXXXXX).')
            return redirect('billing:initiate_mpesa_payment', invoice_id=invoice_id)

        # Here we would integrate with M-Pesa Daraja API
        # For now, we'll simulate the payment process

        # Simulate successful payment
        payment = Payment.objects.create(
            invoice=invoice,
            amount_paid=invoice.amount,
            mpesa_code=f"MPESA{datetime.now().strftime('%Y%m%d%H%M%S')}",
        )

        # Update invoice status
        invoice.status = 'PAID'
        invoice.save()

        messages.success(request, f'Payment of KSh {invoice.amount} successful! M-Pesa code: {payment.mpesa_code}')
        return redirect('customers:customer_invoice_detail', invoice_id=invoice.id)

    context = {
        'invoice': invoice,
        'customer': customer,
    }

    return render(request, 'billing/mpesa_payment.html', context)

@csrf_exempt
def mpesa_callback(request):
    """Handle M-Pesa payment callback"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Extract payment details from callback
            merchant_request_id = data.get('Body', {}).get('stkCallback', {}).get('MerchantRequestID')
            checkout_request_id = data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID')
            result_code = data.get('Body', {}).get('stkCallback', {}).get('ResultCode')
            result_desc = data.get('Body', {}).get('stkCallback', {}).get('ResultDesc')

            if result_code == 0:
                # Payment successful
                callback_metadata = data.get('Body', {}).get('stkCallback', {}).get('CallbackMetadata', {}).get('Item', [])

                # Extract relevant data
                amount = None
                mpesa_receipt_number = None
                transaction_date = None
                phone_number = None

                for item in callback_metadata:
                    if item.get('Name') == 'Amount':
                        amount = item.get('Value')
                    elif item.get('Name') == 'MpesaReceiptNumber':
                        mpesa_receipt_number = item.get('Value')
                    elif item.get('Name') == 'TransactionDate':
                        transaction_date = item.get('Value')
                    elif item.get('Name') == 'PhoneNumber':
                        phone_number = item.get('Value')

                # Find and update the corresponding invoice
                # This would require storing checkout_request_id when initiating payment
                # For now, we'll assume the payment is processed

                return JsonResponse({'status': 'success', 'message': 'Payment processed successfully'})

            else:
                # Payment failed
                return JsonResponse({'status': 'failed', 'message': result_desc})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def get_mpesa_access_token():
    """Get M-Pesa access token"""
    # This would integrate with M-Pesa Daraja API
    # For development, we'll return a mock token
    return "mock_access_token"

def initiate_stk_push(phone_number, amount, account_reference, transaction_desc):
    """Initiate M-Pesa STK Push"""
    # This would make actual API calls to M-Pesa
    # For development, we'll simulate the response

    # Mock successful response
    return {
        'MerchantRequestID': 'mock_merchant_request_id',
        'CheckoutRequestID': 'mock_checkout_request_id',
        'ResponseCode': '0',
        'ResponseDescription': 'Success. Request accepted for processing',
        'CustomerMessage': 'Success. Request accepted for processing'
    }
