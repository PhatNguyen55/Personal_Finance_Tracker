from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    """Model cho hạng mục thu/chi"""
    TYPE_CHOICES = [
        ('income', 'Thu nhập'),
        ('expense', 'Chi tiêu'),
    ]
    
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ('name', 'type', 'user')

class Wallet(models.Model):
    """Model cho ví/tài khoản"""
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.balance})"

class Transaction(models.Model):
    """Model cho các giao dịch thu/chi"""
    TYPE_CHOICES = [
        ('income', 'Thu nhập'),
        ('expense', 'Chi tiêu'),
    ]
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='transactions')
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    description = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_type_display()}: {self.amount} - {self.category}"
    
    def save(self, *args, **kwargs):
        # Xử lý cập nhật số dư ví
        is_new = self.pk is None
        
        if not is_new:
            # Lấy transaction cũ trước khi cập nhật
            old_transaction = Transaction.objects.get(pk=self.pk)
            # Hoàn lại số dư trước khi cập nhật
            if old_transaction.type == 'income':
                old_transaction.wallet.balance -= old_transaction.amount
            else:
                old_transaction.wallet.balance += old_transaction.amount
            old_transaction.wallet.save()
        
        # Cập nhật số dư hiện tại
        if self.type == 'income':
            self.wallet.balance += self.amount
        else:
            self.wallet.balance -= self.amount
        self.wallet.save()
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Xử lý cập nhật số dư ví khi xóa giao dịch
        if self.type == 'income':
            self.wallet.balance -= self.amount
        else:
            self.wallet.balance += self.amount
        self.wallet.save()
        
        super().delete(*args, **kwargs)