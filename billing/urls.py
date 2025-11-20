from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Web views
    path('mpesa/payment/<int:invoice_id>/', views.initiate_mpesa_payment, name='initiate_mpesa_payment'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),

    # API views
    path('api/invoices/', views.api_customer_invoices, name='api_customer_invoices'),
    path('api/payments/', views.api_customer_payments, name='api_customer_payments'),
    path('api/invoices/list/', views.InvoiceListAPIView.as_view(), name='invoice_list_api'),
    path('api/invoices/<int:pk>/', views.InvoiceDetailAPIView.as_view(), name='invoice_detail_api'),
]
