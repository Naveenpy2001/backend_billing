from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    shop_name = models.CharField(max_length=225)
    username = models.CharField(max_length=225,unique=False)
    email = models.EmailField(unique=True)
    gst_number = models.CharField(max_length=225,null=True,blank=True)
    phone = models.CharField(max_length=225)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    upi_id = models.CharField(max_length=100, null=True, blank=True)
    signature = models.ImageField(upload_to='signatures/', null=True, blank=True)
    show_customer_details = models.BooleanField(default=True)
    print_automatically = models.BooleanField(default=False)
    show_signature = models.BooleanField(default=True)

    referred_by = models.CharField(max_length=225,null=True,blank=True)

    plan_status = models.CharField(max_length=100, default='inactive')
    

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
    

class Plan(models.Model):
    name = models.CharField(max_length=100)  # e.g., "5 Minute Test Plan"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = models.IntegerField()  # use minutes for quick testing

    def __str__(self):
        return self.name
    

class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    payment_id = models.CharField(max_length=255, null=True, blank=True)  # Razorpay payment id
    status = models.CharField(max_length=50, default='active')  # active/expired

    def save(self, *args, **kwargs):
        if not self.end_date and self.plan:
            self.end_date = self.start_date + timedelta(minutes=self.plan.duration_minutes)
        super().save(*args, **kwargs)

    def is_active(self):
        return timezone.now() <= self.end_date

class BankDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bank_details')
    bank_name = models.CharField(max_length=225)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    branch = models.CharField(max_length=225, null=True, blank=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"
    
class TermsAndConditions(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='terms')
    term = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.user.email} - Term {self.order}"



class Ticket(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        (1, '1 - Lowest'),
        (2, '2 - Low'),
        (3, '3 - Medium'),
        (4, '4 - High'),
        (5, '5 - Highest'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    admin_feedback = models.TextField(blank=True, null=True)
    feedback_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.subject} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Update feedback date when admin feedback is added/changed
        if self.admin_feedback and not self.feedback_date:
            self.feedback_date = timezone.now()
        elif not self.admin_feedback:
            self.feedback_date = None
        super().save(*args, **kwargs)


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='ticket_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.ticket.subject}"

    
from datetime import date,timedelta

class Product(models.Model):
    product_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    product_name = models.CharField(max_length=255)
    category = models.CharField(max_length=225, null=True, blank=True)
    unit = models.CharField(max_length=225, null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=0)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expiry_date = models.DateField(blank=True, null=True)
    manufacturer = models.CharField(max_length=100, blank=True, null=True)
    supplier = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_name

    def save(self, *args, **kwargs):
        if not self.product_code:
            last_product = Product.objects.order_by('-id').first()
            last_id = last_product.id if last_product else 0
            self.product_code = f"PRD-{last_id + 1:04d}"
        super().save(*args, **kwargs)

    
    @property
    def expiry_status(self):
        if not self.expiry_date:
            return "No expiry"

        today = date.today()

        if self.expiry_date < today:
            return "Expired"
        elif self.expiry_date == today:
            return "Expires Today"
        elif self.expiry_date <= today + timedelta(days=7):
             days_left = (self.expiry_date - today).days
             return f"Expires in {days_left} days"
        else:
            return f"Valid Until {self.expiry_date}"

    @property
    def days_to_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days




class Sale(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    sold_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    sale_date = models.DateTimeField(auto_now_add=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    customer_gst = models.CharField(max_length=15, blank=True, null=True)
    customer_state = models.CharField(max_length=100, blank=True, null=True)
    customer_state_code = models.CharField(max_length=20, blank=True, null=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, default='cash')
    notes = models.TextField(blank=True, null=True)
    include_gst = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.total_amount}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last_invoice = Sale.objects.order_by('-id').first()
            last_number = int(last_invoice.invoice_number.split('-')[1]) if last_invoice and last_invoice.invoice_number else 0
            self.invoice_number = f"INV-{last_number + 1:05d}"
        super().save(*args, **kwargs)

from decimal import Decimal

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    product_name = models.CharField(max_length=225,blank=True,null=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxable_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        self.taxable_amount = self.sale_price * self.quantity
        self.tax_amount = self.taxable_amount * (Decimal(str(self.tax_rate)) / Decimal('100'))
        self.total_amount = self.taxable_amount + self.tax_amount
        super().save(*args, **kwargs)
        
        # Update product stock
        self.product.stock_quantity -= self.quantity
        self.product.save()


class AddCustomers(models.Model):
    CUSTOMER_TYPES = (
        ('retail', 'Retail Customer'),
        ('wholesale', 'Wholesale Customer'),
        ('business', 'Business Customer'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )
    added_by = models.ForeignKey(User,on_delete=models.CASCADE,null=True, related_name='customers')
    name = models.CharField(max_length=225)
    phone = models.CharField(max_length=225)
    email = models.EmailField()
    address = models.CharField(max_length=225)
    city = models.CharField(max_length=225)
    state = models.CharField(max_length=225)
    zip = models.CharField(max_length=225)
    country = models.CharField(max_length=225)
    customerType = models.CharField(max_length=225,choices=CUSTOMER_TYPES,default='retail')
    taxId = models.CharField(max_length=225)
    notes = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('can_activate_customer', 'Can activate customer'),
            ('can_deactivate_customer', 'Can deactivate customer'),
        ]




from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AddVendor(models.Model):
    VENDOR_TYPE_CHOICES = [
        ('supplier', 'Supplier'),
        ('manufacturer', 'Manufacturer'),
        ('distributor', 'Distributor'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vendors')
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    zip = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=50, default='India')
    vendor_type = models.CharField(max_length=20, choices=VENDOR_TYPE_CHOICES, default='supplier')
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vendor'
        verbose_name_plural = 'Vendors'



from django.db import models
from django.conf import settings

class BillSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bill_settings'
    )
    header = models.CharField(max_length=100, default='Your Business Name')
    subheader = models.CharField(max_length=100, default='Your Business Slogan')
    footer = models.CharField(max_length=200, default='Thank you for your business!')
    tax_enabled = models.BooleanField(default=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    discount_enabled = models.BooleanField(default=False)
    print_automatically = models.BooleanField(default=False)
    show_logo = models.BooleanField(default=True)
    logo = models.ImageField(upload_to='bill_settings/logos/', null=True, blank=True)
    show_signature = models.BooleanField(default=True)
    signature = models.ImageField(upload_to='bill_settings/signatures/', null=True, blank=True)
    gst_number = models.CharField(max_length=50, blank=True, default='')
    upi_id = models.CharField(max_length=100, blank=True, default='')
    terms_and_conditions = models.TextField(default='Goods once sold will not be taken back.')
    show_customer_details = models.BooleanField(default=True)
    default_payment_method = models.CharField(
        max_length=20,
        choices=[('cash', 'Cash'), ('card', 'Card'), ('upi', 'UPI'), ('other', 'Other')],
        default='cash'
    )
    default_currency = models.CharField(max_length=3, default='INR')
    default_category = models.CharField(max_length=50, blank=True, default='')
    default_unit = models.CharField(max_length=20, blank=True, default='')
    default_gst_rate = models.CharField(max_length=5, default='18')
    tax_type_on_sale = models.CharField(
        max_length=10,
        choices=[('inclusive', 'Inclusive'), ('exclusive', 'Exclusive')],
        default='inclusive'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bill Settings for {self.user.username}"



User = get_user_model()

class DataBackup(models.Model):
    BACKUP_TYPES = [
        ('full', 'Full Backup'),
        ('partial', 'Partial Backup'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backups')
    created_at = models.DateTimeField(auto_now_add=True)
    size = models.BigIntegerField()  # Size in bytes
    backup_type = models.CharField(max_length=10, choices=BACKUP_TYPES)
    file = models.FileField(upload_to='backups/')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Backup {self.id} - {self.user.username}"
    


