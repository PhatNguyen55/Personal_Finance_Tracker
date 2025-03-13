from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Category, Wallet, Transaction

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'type')
    
    def create(self, validated_data):
        # Gán user hiện tại vào category
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'name', 'balance', 'initial_balance', 'created_at', 'updated_at')
        read_only_fields = ('balance', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        # Gán user hiện tại vào wallet
        validated_data['user'] = self.context['request'].user
        # Khởi tạo balance từ initial_balance
        validated_data['balance'] = validated_data.get('initial_balance', 0)
        return super().create(validated_data)

class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    wallet_name = serializers.CharField(source='wallet.name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = ('id', 'amount', 'type', 'category', 'category_name', 'wallet', 
                  'wallet_name', 'description', 'date', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        # Kiểm tra loại category có phù hợp với loại transaction không
        if data.get('category') and data.get('type'):
            if data['category'].type != data['type']:
                raise serializers.ValidationError(
                    f"Category phải cùng loại với transaction (thu/chi)."
                )
        
        # Kiểm tra wallet có thuộc user hiện tại không
        if data.get('wallet'):
            if data['wallet'].user != self.context['request'].user:
                raise serializers.ValidationError("Bạn không có quyền truy cập tài khoản này.")
        
        return data
    
    def create(self, validated_data):
        # Gán user hiện tại vào transaction
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class TransactionReportSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    
    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Ngày bắt đầu phải trước ngày kết thúc")
        return data