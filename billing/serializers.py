from rest_framework import serializers
from .models import CustomerService, Invoice, Payment

class CustomerServiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.user.get_full_name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_price = serializers.DecimalField(source='plan.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CustomerService
        fields = ['id', 'customer', 'customer_name', 'plan', 'plan_name', 'plan_price', 'status', 'start_date', 'end_date', 'created_at']
        read_only_fields = ['id', 'created_at']

class InvoiceSerializer(serializers.ModelSerializer):
    customer_service_details = CustomerServiceSerializer(source='customer_service', read_only=True)
    total_payments = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'customer_service', 'customer_service_details', 'amount', 'status', 'due_date', 'created_at', 'total_payments']
        read_only_fields = ['id', 'created_at']

    def get_total_payments(self, obj):
        return sum(payment.amount_paid for payment in obj.payment_set.all())

class PaymentSerializer(serializers.ModelSerializer):
    invoice_details = InvoiceSerializer(source='invoice', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'invoice', 'invoice_details', 'amount_paid', 'mpesa_code', 'timestamp']
        read_only_fields = ['id', 'timestamp']
