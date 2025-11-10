from django.contrib import admin
from .models import ServicePlan

@admin.register(ServicePlan)
class ServicePlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'speed_mbps', 'price')
    search_fields = ('name',)
    ordering = ('speed_mbps',)
