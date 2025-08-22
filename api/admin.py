from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, AddCustomers, AddVendor, BillSettings, DataBackup

# Unregister the default User admin if it's registered
# admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    list_display = ('email', 'username', 'shop_name', 'phone', 'gst_number', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'date_joined')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'shop_name', 'phone', 'gst_number', 'profile_photo')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'shop_name', 'phone', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'username', 'shop_name', 'phone')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_code', 'category', 'selling_price', 'stock_quantity', 'created_by', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('product_name', 'product_code', 'barcode')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(AddCustomers)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'customerType', 'status', 'added_by', 'created_at')
    list_filter = ('customerType', 'status', 'city', 'state')
    search_fields = ('name', 'phone', 'email', 'taxId')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(AddVendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'vendor_type', 'status', 'created_by', 'created_at')
    list_filter = ('vendor_type', 'status', 'city', 'state')
    search_fields = ('name', 'phone', 'email', 'tax_id')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(BillSettings)
class BillSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'header', 'tax_enabled', 'tax_rate', 'created_at')
    search_fields = ('user__username', 'user__email', 'header')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(DataBackup)
class DataBackupAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'size', 'backup_type', 'is_active')
    list_filter = ('backup_type', 'is_active')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'