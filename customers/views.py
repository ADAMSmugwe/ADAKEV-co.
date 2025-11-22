from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Customer
from .forms import CustomUserCreationForm, CustomerRegistrationForm
from .serializers import CustomerSerializer
from billing.models import Invoice

# Existing views...

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_customer_profile(request):
    """API endpoint for customer profile"""
    try:
        customer = Customer.objects.get(user=request.user)
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer profile not found'}, status=404)

class CustomerProfileAPIView(generics.RetrieveUpdateAPIView):
    """API view for customer profile management"""
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return Customer.objects.get(user=self.request.user)

def customer_login(request):
    """Customer login view"""
    if request.user.is_authenticated:
        return redirect('customers:customer_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check if user has a customer profile
            try:
                customer = Customer.objects.get(user=user)
                login(request, user)
                messages.success(request, f'Welcome back, {customer.user.get_full_name()}!')
                return redirect('customers:customer_dashboard')
            except Customer.DoesNotExist:
                messages.error(request, 'You are not registered as a customer.')
                return redirect('customers:customer_login')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'customers/login.html')

def customer_logout(request):
    """Customer logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('customers:customer_login')

def customer_register(request):
    """Customer registration view"""
    if request.user.is_authenticated:
        return redirect('customers:customer_dashboard')

    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        customer_form = CustomerRegistrationForm(request.POST)

        if user_form.is_valid() and customer_form.is_valid():
            # Save user
            user = user_form.save()

            # Save customer profile
            customer = customer_form.save(commit=False)
            customer.user = user
            customer.save()

            # Log in the user
            login(request, user)
            messages.success(request, f'Account created successfully! Welcome, {user.get_full_name()}!')
            return redirect('customers:customer_dashboard')
    else:
        user_form = CustomUserCreationForm()
        customer_form = CustomerRegistrationForm()

    return render(request, 'customers/register.html', {
        'user_form': user_form,
        'customer_form': customer_form
    })

@login_required
def customer_dashboard(request):
    """Customer dashboard view"""
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('customer_login')

    # Get customer's subscriptions, invoices, and payments
    subscriptions = customer.customerservice_set.all()
    invoices = []
    payments = []

    for subscription in subscriptions:
        invoices.extend(subscription.invoice_set.all())
        for invoice in subscription.invoice_set.all():
            payments.extend(invoice.payment_set.all())

    context = {
        'customer': customer,
        'subscriptions': subscriptions,
        'invoices': invoices,
        'payments': payments,
    }

    return render(request, 'customers/dashboard.html', context)

@login_required
def customer_invoices(request):
    """View all customer invoices"""
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('customer_login')

    # Get all invoices for this customer
    subscriptions = customer.customerservice_set.all()
    invoices = []

    for subscription in subscriptions:
        invoices.extend(subscription.invoice_set.all().order_by('-created_at'))

    context = {
        'customer': customer,
        'invoices': invoices,
    }

    return render(request, 'customers/invoices.html', context)

@login_required
def customer_invoice_detail(request, invoice_id):
    """View specific invoice details"""
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('customer_login')

    try:
        invoice = Invoice.objects.get(
            id=invoice_id,
            customer_service__customer=customer
        )
    except Invoice.DoesNotExist:
        messages.error(request, 'Invoice not found.')
        return redirect('customer_invoices')

    # Get payment history for this invoice
    payments = invoice.payment_set.all().order_by('-timestamp')

    context = {
        'customer': customer,
        'invoice': invoice,
        'payments': payments,
    }

    return render(request, 'customers/invoice_detail.html', context)
