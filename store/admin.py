from django.contrib import admin
from .models import Category, Product, CartItem, ScrollingText, Review

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

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'created_at')
    search_fields = ('user__username', 'content')

admin.site.register(CartItem)
admin.site.register(ScrollingText)