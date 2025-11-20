from rest_framework import serializers
from .models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'user_full_name', 'user_email', 'phone_number', 'address', 'id_number', 'created_at']
        read_only_fields = ['id', 'created_at']
