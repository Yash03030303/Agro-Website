from django.contrib import admin

# Register your models here.

from .models import Category, Product, CartItem, ScrollingText

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price')
    list_editable = ('price',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'category__name')

admin.site.register(CartItem)
admin.site.register(ScrollingText)