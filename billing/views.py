from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import requests
import os
import base64
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

        # Initiate M-Pesa STK Push
        stk_response = initiate_stk_push(phone_number, float(invoice.amount), f"Invoice-{invoice.id}", f"Payment for Invoice #{invoice.id}")

        if stk_response.get('ResponseCode') == '0':
            # Payment initiated successfully
            checkout_request_id = stk_response.get('CheckoutRequestID')
            
            # Create Payment record with checkout_request_id
            payment = Payment.objects.create(
                invoice=invoice,
                amount_paid=invoice.amount,
                mpesa_code=f"PENDING-{checkout_request_id}",  # Temporary code until callback
                checkout_request_id=checkout_request_id,
            )

            messages.success(request, f'M-Pesa STK Push initiated! Please check your phone to complete the payment. Transaction ID: {checkout_request_id}')
            return redirect('customers:customer_invoice_detail', invoice_id=invoice.id)
        else:
            # Payment initiation failed
            messages.error(request, f'Failed to initiate payment: {stk_response.get("ResponseDescription", "Unknown error")}')
            return redirect('billing:initiate_mpesa_payment', invoice_id=invoice_id)

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

                # Find the payment using CheckoutRequestID
                try:
                    payment = Payment.objects.get(checkout_request_id=checkout_request_id)
                    
                    # Update payment details
                    payment.mpesa_code = mpesa_receipt_number
                    payment.amount_paid = amount
                    payment.save()

                    # Update invoice status
                    invoice = payment.invoice
                    invoice.status = 'PAID'
                    invoice.save()

                    # Update customer service status to ACTIVE
                    customer_service = invoice.customer_service
                    customer_service.status = 'ACTIVE'
                    customer_service.save()

                    return JsonResponse({'status': 'success', 'message': 'Payment processed successfully'})

                except Payment.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Payment record not found'})

            else:
                # Payment failed
                return JsonResponse({'status': 'failed', 'message': result_desc})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def get_mpesa_access_token():
    """Get M-Pesa access token"""
    consumer_key = os.getenv('MPESA_CONSUMER_KEY')
    consumer_secret = os.getenv('MPESA_CONSUMER_SECRET')
    api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'

    try:
        response = requests.get(api_url, auth=(consumer_key, consumer_secret))
        response.raise_for_status()
        return response.json()['access_token']
    except requests.RequestException as e:
        print(f"Error getting access token: {e}")
        return None

def initiate_stk_push(phone_number, amount, account_reference, transaction_desc):
    """Initiate M-Pesa STK Push"""
    access_token = get_mpesa_access_token()
    if not access_token:
        return {'ResponseCode': '1', 'ResponseDescription': 'Failed to get access token'}

    api_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    headers = {'Authorization': f'Bearer {access_token}'}

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{os.getenv('MPESA_SHORTCODE')}{os.getenv('MPESA_PASSKEY')}{timestamp}".encode()).decode()

    payload = {
        'BusinessShortCode': os.getenv('MPESA_SHORTCODE'),
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': amount,
        'PartyA': phone_number,
        'PartyB': os.getenv('MPESA_SHORTCODE'),
        'PhoneNumber': phone_number,
        'CallBackURL': os.getenv('MPESA_CALLBACK_URL'),
        'AccountReference': account_reference,
        'TransactionDesc': transaction_desc
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error initiating STK push: {e}")
        return {'ResponseCode': '1', 'ResponseDescription': 'Failed to initiate STK push'}
