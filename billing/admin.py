from django.contrib import admin
from .models import CustomerService, Invoice, Payment

@admin.register(CustomerService)
class CustomerServiceAdmin(admin.ModelAdmin):
    list_display = ('customer', 'plan', 'status', 'start_date')
    list_filter = ('status',)
    search_fields = ('customer__user__username', 'customer__phone_number')
    ordering = ('-created_at',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_service', 'amount', 'status', 'due_date')
    list_filter = ('status',)
    search_fields = ('customer_service__customer__user__username',)
    ordering = ('-created_at',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount_paid', 'mpesa_code', 'timestamp')
    search_fields = ('mpesa_code', 'invoice__customer_service__customer__user__username')
    ordering = ('-timestamp',)
