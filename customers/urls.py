from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('login/', views.customer_login, name='customer_login'),
    path('logout/', views.customer_logout, name='customer_logout'),
    path('register/', views.customer_register, name='customer_register'),
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('invoices/', views.customer_invoices, name='customer_invoices'),
    path('invoices/<int:invoice_id>/', views.customer_invoice_detail, name='customer_invoice_detail'),

    # API URLs
    path('api/profile/', views.api_customer_profile, name='api_customer_profile'),
    path('api/profile/update/', views.CustomerProfileAPIView.as_view(), name='api_customer_profile_update'),
]
