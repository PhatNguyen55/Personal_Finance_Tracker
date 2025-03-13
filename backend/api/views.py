from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Category, Wallet, Transaction
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from .serializers import (
    UserSerializer, CategorySerializer, WalletSerializer, 
    TransactionSerializer, TransactionReportSerializer
)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Tạo JWT Token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Tạo danh mục mặc định
        default_income_categories = ["Tiền lương", "Lãi tiết kiệm", "Thu nhập phụ", "Quà tặng"]
        default_expense_categories = ["Ăn uống", "Dịch vụ sinh hoạt", "Di chuyển", "Mua sắm", "Giải trí"]
        
        for name in default_income_categories:
            Category.objects.create(name=name, type='income', user=user)
            
        for name in default_expense_categories:
            Category.objects.create(name=name, type='expense', user=user)
        
        return Response({
            "user": serializer.data,
            "refresh": str(refresh),
            "access": access_token,
        }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return Response({
            "refresh": response.data["refresh"],
            "access": response.data["access"]
        })

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()  # Đưa token vào danh sách đen
            return Response({"message": "Đăng xuất thành công"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def income(self, request):
        """Lấy danh sách các hạng mục thu nhập"""
        income_categories = self.get_queryset().filter(type='income')
        serializer = self.get_serializer(income_categories, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expense(self, request):
        """Lấy danh sách các hạng mục chi tiêu"""
        expense_categories = self.get_queryset().filter(type='expense')
        serializer = self.get_serializer(expense_categories, many=True)
        return Response(serializer.data)

class WalletViewSet(viewsets.ModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Transaction.objects.filter(user=user)
        
        # Lọc theo loại giao dịch (thu/chi)
        transaction_type = self.request.query_params.get('type', None)
        if transaction_type:
            queryset = queryset.filter(type=transaction_type)
        
        # Lọc theo tài khoản ví
        wallet_id = self.request.query_params.get('wallet', None)
        if wallet_id:
            queryset = queryset.filter(wallet__id=wallet_id)
        
        # Lọc theo hạng mục
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category__id=category_id)
        
        # Lọc theo khoảng thời gian
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date')
    
    @action(detail=False, methods=['get'])
    def report(self, request):
        """Báo cáo tổng quan thu chi"""
        user = request.user
        serializer = TransactionReportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        
        # Thống kê tổng thu và chi
        income_sum = Transaction.objects.filter(
            user=user, 
            type='income',
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expense_sum = Transaction.objects.filter(
            user=user, 
            type='expense',
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Số dư ví
        wallets = Wallet.objects.filter(user=user)
        wallet_balances = [
            {
                'id': wallet.id,
                'name': wallet.name,
                'balance': wallet.balance
            } for wallet in wallets
        ]
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_income': income_sum,
                'total_expense': expense_sum,
                'net': income_sum - expense_sum
            },
            'wallets': wallet_balances
        })
    
    @action(detail=False, methods=['get'])
    def category_analysis(self, request):
        """Phân tích chi tiêu theo hạng mục"""
        user = request.user
        serializer = TransactionReportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        
        # Thống kê chi tiêu theo hạng mục
        expense_by_category = Transaction.objects.filter(
            user=user,
            type='expense',
            date__gte=start_date,
            date__lte=end_date
        ).values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Thống kê thu nhập theo hạng mục
        income_by_category = Transaction.objects.filter(
            user=user,
            type='income',
            date__gte=start_date,
            date__lte=end_date
        ).values('category__name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'expenses_by_category': expense_by_category,
            'income_by_category': income_by_category
        })
    
    @action(detail=False, methods=['get'])
    def time_analysis(self, request):
        """Phân tích chi tiêu theo thời gian"""
        user = request.user
        serializer = TransactionReportSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        
        # Phân tích theo tháng
        monthly_data = Transaction.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date
        ).annotate(
            month=TruncMonth('date')
        ).values('month', 'type').annotate(
            total=Sum('amount')
        ).order_by('month', 'type')
        
        # Định dạng dữ liệu theo tháng
        monthly_summary = {}
        for item in monthly_data:
            month_str = item['month'].strftime('%Y-%m')
            if month_str not in monthly_summary:
                monthly_summary[month_str] = {
                    'income': 0,
                    'expense': 0,
                    'net': 0
                }
            
            monthly_summary[month_str][item['type']] = item['total']
            monthly_summary[month_str]['net'] = (
                monthly_summary[month_str]['income'] - monthly_summary[month_str]['expense']
            )
        
        # Chuyển đổi từ dict sang list để dễ xử lý ở frontend
        monthly_result = [
            {
                'month': month,
                'income': data['income'],
                'expense': data['expense'],
                'net': data['net']
            } for month, data in monthly_summary.items()
        ]
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'monthly_analysis': monthly_result
        })