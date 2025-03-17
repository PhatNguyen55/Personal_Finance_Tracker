from django.contrib import admin
from .models import Expense, Category


class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('amount', 'description', 'owner', 'category', 'date',)
    search_fields = ('description', 'category', 'date',)

    list_per_page = 5

# Register your models here.
admin.site.register(Expense)
admin.site.register(Category)