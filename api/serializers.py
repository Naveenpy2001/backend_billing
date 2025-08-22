from rest_framework import serializers
from .models import *
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    profile_photo = serializers.FileField(required=False, allow_null=True)
    class Meta:
        model = User
        fields = ['email','password','gst_number','confirm_password','shop_name','username','phone','profile_photo','referred_by']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user
    
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                return user
            raise serializers.ValidationError("Unable to log in with provided credentials.")
        raise serializers.ValidationError("Must include 'email' and 'password'.")


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        User = get_user_model()
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        
        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
            
        return attrs
    




class TicketAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAttachment
        fields = ['id', 'file', 'uploaded_at']
        read_only_fields = ['uploaded_at']

class TicketSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'user', 'subject', 'description', 
            'status', 'status_display', 'priority', 'priority_display',
            'created_at', 'updated_at', 'admin_feedback', 'feedback_date',
            'attachments'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at', 'feedback_date']

class TicketCreateSerializer(serializers.ModelSerializer):
    attachments = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False),
        write_only=True,
        required=False
    )

    class Meta:
        model = Ticket
        fields = ['subject', 'description', 'priority', 'attachments']
        extra_kwargs = {
            'priority': {'required': True}
        }

    def create(self, validated_data):
        attachments_data = validated_data.pop('attachments', [])
        ticket = Ticket.objects.create(
            user=self.context['request'].user,  # user set here
            **validated_data
        )
        
        for attachment in attachments_data:
            TicketAttachment.objects.create(
                ticket=ticket,
                file=attachment
            )
        
        return ticket


class TicketFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['id', 'status', 'admin_feedback']
        extra_kwargs = {
            'admin_feedback': {'required': True}
        }




class ProductSerializer(serializers.ModelSerializer):
    expiry_status = serializers.ReadOnlyField()
    days_to_expiry = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = '__all__'
        

class CustomerSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='added_by', read_only=True)
    
    class Meta:
        model = AddCustomers
        fields = '__all__'
        read_only_fields = ('added_by', 'created_at', 'updated_at')


class CustomerStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AddCustomers.STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)


class AddVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddVendor
        fields = '__all__'
        read_only_fields = ('created_by', 'created_at', 'updated_at')

class BillSettingsSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    signature_url = serializers.SerializerMethodField()

    class Meta:
        model = BillSettings
        fields = [
            'id', 'header', 'subheader', 'footer', 'tax_enabled', 'tax_rate',
            'discount_enabled', 'print_automatically', 'show_logo', 'logo', 'logo_url',
            'show_signature', 'signature', 'signature_url', 'gst_number', 'upi_id',
            'terms_and_conditions', 'show_customer_details', 'default_payment_method',
            'default_currency', 'default_category', 'default_unit', 'default_gst_rate',
            'tax_type_on_sale'
        ]
        extra_kwargs = {
            'logo': {'write_only': True, 'required': False},
            'signature': {'write_only': True, 'required': False},
        }

    def get_logo_url(self, obj):
        if obj.logo:
            return self.context['request'].build_absolute_uri(obj.logo.url)
        return None

    def get_signature_url(self, obj):
        if obj.signature:
            return self.context['request'].build_absolute_uri(obj.signature.url)
        return None
    

class DataBackupSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataBackup
        fields = ['id', 'created_at', 'size', 'backup_type', 'file']
        read_only_fields = ['id', 'created_at', 'size']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class SimpleProductSerializer(serializers.ModelSerializer):
    sales_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'product_code', 'product_name', 'category', 
                 'stock_quantity', 'selling_price', 'sales_count']

    def get_sales_count(self, obj):
        return Sale.objects.filter(product=obj).count()

class SaleDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = ['id', 'quantity', 'sale_date', 'customer_name']

class ProductWithSalesSerializer(serializers.ModelSerializer):
    sales = serializers.SerializerMethodField()
    expiry_status = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = ['id', 'product_code', 'product_name', 'category', 
                 'stock_quantity', 'selling_price', 'sales','expiry_status']

    def get_sales(self, obj):
        sales = Sale.objects.filter(product=obj).order_by('-sale_date')
        return SaleDetailSerializer(sales, many=True).data

class UserProductsWithSalesSerializer(serializers.ModelSerializer):
    products = ProductWithSalesSerializer(many=True, read_only=True, source='product_set')
    
    class Meta:
        model = User
        fields = ['id', 'shop_name', 'email', 'phone', 'profile_photo', 'products']



class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    
    class Meta:
        model = SaleItem
        fields = ['id', 'product', 'product_id', 'product_name', 'quantity', 'sale_price', 
                 'tax_rate', 'tax_amount', 'taxable_amount', 'total_amount']

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    sold_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Sale
        fields = ['id', 'invoice_number', 'sold_by', 'sale_date', 'customer_name', 
                 'customer_phone', 'customer_address', 'customer_gst', 'customer_state',
                 'customer_state_code', 'discount', 'tax_amount', 'taxable_amount',
                 'total_amount', 'payment_method', 'notes', 'include_gst', 'items']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        sale = Sale.objects.create(**validated_data)
        
        for item_data in items_data:
            product = item_data['product']
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=item_data['quantity'],
                sale_price=product.selling_price,
                tax_rate=product.tax_rate or 0
            )
        
        # Calculate totals
        sale.taxable_amount = sum(item.taxable_amount for item in sale.items.all())
        sale.tax_amount = sum(item.tax_amount for item in sale.items.all())
        sale.total_amount = sale.taxable_amount + sale.tax_amount - sale.discount
        sale.save()
        
        return sale
    



class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = '__all__'
        read_only_fields = ('user',)

class TermsAndConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsAndConditions
        fields = '__all__'
        read_only_fields = ('user',)

class UserSerializerBank(serializers.ModelSerializer):
    bank_details = BankDetailsSerializer(required=False)
    terms = TermsAndConditionsSerializer(many=True, required=False)
    profile_photo = serializers.ImageField(required=False, allow_null=True)
    signature = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'shop_name', 'username', 'email', 'gst_number', 'phone',
            'profile_photo', 'address', 'upi_id', 'signature',
            'show_customer_details', 'print_automatically', 'show_signature',
            'bank_details', 'terms','plan_status'
        ]
        read_only_fields = ('email', 'username')

    def update(self, instance, validated_data):
        bank_details_data = validated_data.pop('bank_details', None)
        terms_data = validated_data.pop('terms', None)

        # Update User fields
        instance = super().update(instance, validated_data)

        # Update or create BankDetails
        if bank_details_data:
            bank_details, created = BankDetails.objects.update_or_create(
                user=instance,
                defaults=bank_details_data
            )

        # Update Terms and Conditions
        if terms_data is not None:
            # First delete all existing terms
            instance.terms.all().delete()
            # Then create new ones
            for term_data in terms_data:
                TermsAndConditions.objects.create(user=instance, **term_data)

        return instance