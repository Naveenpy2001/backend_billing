from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import viewsets, filters, permissions

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
import time
import os
from django.db import transaction
from django.core.files.storage import default_storage

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self,request):
        serializer = RegisterSerializer(data = request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    'Message' : 'User Registered Successfully.!',
                    'user' : UserSerializer(user).data
                },status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)



class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['new_password']
            
            try:
                user = User.objects.get(email=email)
                user.set_password(new_password)
                user.save()
                return Response(
                    {'message': 'Password updated successfully.'}, 
                    status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckEmailView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        exists = User.objects.filter(email=email).exists()
        return Response({'exists': exists}, status=status.HTTP_200_OK)


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializerBank
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'patch', 'head', 'options'] 

    def get_object(self):
        return self.request.user

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=['put'], name='Update Shop Details')
    def shop_details(self, request):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['product_name', 'product_code', 'barcode']
    filterset_fields = ['category', 'unit', 'is_active']


    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        queryset = queryset.filter(created_by=user)

        expiry_filter = self.request.query_params.get('expiry')
        today = date.today()

        if expiry_filter == 'expired':
            queryset = queryset.filter(expiry_date__lt=today)
        elif expiry_filter == 'expiring_soon':
            next_week = today + timedelta(days=7)
            queryset = queryset.filter(expiry_date__range=(today, next_week))

        return queryset


    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'phone', 'email', 'city']
    filterset_fields = ['customerType', 'status', 'country']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return AddCustomers.objects.filter(added_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def activate(self, request, pk=None):
        customer = self.get_object()
        customer.status = 'active'
        customer.save()
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def deactivate(self, request, pk=None):
        customer = self.get_object()
        customer.status = 'inactive'
        customer.save()
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], serializer_class=CustomerStatusSerializer)
    def set_status(self, request, pk=None):
        customer = self.get_object()
        serializer = CustomerStatusSerializer(data=request.data)
        
        if serializer.is_valid():
            customer.status = serializer.validated_data['status']
            customer.save()
            
            # You could log the reason if needed
            reason = serializer.validated_data.get('reason', '')
            # log_status_change(customer, request.user, reason)
            
            return Response({'status': 'status updated'})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

class AddVendorViewSet(viewsets.ModelViewSet):
    queryset = AddVendor.objects.all()
    serializer_class = AddVendorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'contact_person', 'phone']
    filterset_fields = ['vendor_type', 'status', 'country']
    lookup_field = 'id'

    def get_queryset(self):
        return self.queryset.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def search(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"detail": "Vendor deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        vendor = self.get_object()
        vendor.status = 'active'
        vendor.save()
        return Response({'status': 'vendor activated'})

class BillSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = BillSettingsSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch']

    def get_queryset(self):
        return BillSettings.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get', 'put', 'patch'])
    def mine(self, request):
        instance, created = BillSettings.objects.get_or_create(user=request.user)
        
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(instance, data=request.data, partial=request.method == 'PATCH')
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

class DataBackupViewSet(viewsets.ModelViewSet):
    queryset = DataBackup.objects.filter(is_active=True)
    serializer_class = DataBackupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def custom_create_backup(self, request):
        """Create a new backup synchronously"""
        try:
            user = request.user
            backup_data = {
                'user': user.id,
                'backup_type': 'full',
            }
            
            backup_content = f"Backup for user {user.username} at {time.ctime()}"
            file_name = f"backup_{user.id}_{int(time.time())}.bak"
            file_path = default_storage.save(f"backups/{file_name}", ContentFile(backup_content))
            
          
            backup = DataBackup.objects.create(
                user=user,
                size=len(backup_content),
                backup_type='full',
                file=file_path
            )
            
            serializer = self.get_serializer(backup)
            print(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
       
        try:
            backup = self.get_object()

            time.sleep(2)  
            
            return Response(
                {'status': 'success', 'message': 'Backup restored successfully'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='status/(?P<task_id>[^/.]+)')
    def status(self, request, task_id=None):
        
        return Response({'progress': 100})

    def perform_destroy(self, instance):
        
        try:
            
            if instance.file:
                if default_storage.exists(instance.file.name):
                    default_storage.delete(instance.file.name)
            
            
            instance.is_active = False
            instance.save()
            
        except Exception as e:
           
            print(f"Error deleting backup file: {e}")
            instance.is_active = False
            instance.save()

from .permissions import IsAdminUser
class UsersViewSet(viewsets.ModelViewSet):

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        return super().get_queryset()

    # @action(detail=True, methods=['patch'], url_path='status')
    # def toggle_user_status(self, request, pk=None):
    #     user = self.get_object()
    #     # user.is_active = not user.is_active
    #     user.plan_status = 'expired' if not user.is_active else 'active'
    #     user.save()
    #     return Response({'status': 'updated', 'is_active': user.is_active, 'plan_status': user.plan_status})


    @action(detail=True, methods=['patch'], url_path='status')
    def toggle_user_status(self, request, pk=None):
        user = self.get_object()

        # Toggle plan_status manually
        if user.plan_status == 'active':
            user.plan_status = 'expired'
        else:
            user.plan_status = 'active'

        user.save()
        return Response({
            'status': 'updated',
            'plan_status': user.plan_status
        })


from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all().order_by('-sale_date')
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = [
        'customer_name', 
        'sold_by__username',
        'invoice_number',
    ]

    filterset_fields = {
        'sale_date': ['date__gte', 'date__lte'],
        'total_amount': ['gte', 'lte'],
    }
    
    def perform_create(self, serializer):
        serializer.save(sold_by=self.request.user)

    def get_queryset(self):
        return Sale.objects.filter(sold_by=self.request.user)

    
    @action(detail=True, methods=['get'])
    def sale_pdf(self, request, pk=None):
        sale = self.get_object()
        user = request.user  # The logged-in user

        # Get bank details if available
        bank_details = getattr(user, 'bank_details', None)

        # Get terms & conditions if available
        terms = user.terms.order_by('order').values_list('term', flat=True)

        shop_details = {
            'shop_name': user.shop_name,
            'address': user.address or '',
            'phone': user.phone,
            'email': user.email,
            'gst_number': user.gst_number or '',
            'upi_id': user.upi_id or '',
            'signature': user.signature.url if user.signature else None,
            'bank_name': bank_details.bank_name if bank_details else '',
            'account_number': bank_details.account_number if bank_details else '',
            'ifsc_code': bank_details.ifsc_code if bank_details else '',
            'branch': bank_details.branch if bank_details else '',
            'terms': list(terms),  # Pass as list so template can loop
        }

        context = {
            'sale': sale,
            'shop_details': shop_details,
            'date': sale.sale_date.strftime('%Y-%m-%d'),
        }

        template = get_template('sales/invoice_pdf.html')
        html = template.render(context)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{sale.invoice_number}.pdf"'

        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all().order_by('-created_at')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority']
    search_fields = ['subject', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']

    def get_serializer_class(self):
        if self.action == 'create':
            return TicketCreateSerializer
        elif self.action == 'provide_feedback':
            return TicketFeedbackSerializer
        return TicketSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        serializer.save()


    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def provide_feedback(self, request, pk=None):
        ticket = self.get_object()
        serializer = self.get_serializer(ticket, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Only update feedback if status is being changed to Resolved/Closed
        new_status = serializer.validated_data.get('status')
        if new_status in ['Resolved', 'Closed'] and not serializer.validated_data.get('admin_feedback'):
            return Response(
                {'admin_feedback': 'Feedback is required when resolving or closing a ticket.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.save()
        return Response(serializer.data)


class UserViewSetDetail(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserProductsWithSalesSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data)

import pandas as pd
from rest_framework.parsers import MultiPartParser

class ProductImportView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        if 'file' not in request.FILES:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                return Response({'error': 'Unsupported file format'}, 
                               status=status.HTTP_400_BAD_REQUEST)

            
            df.columns = df.columns.str.lower().str.replace(' ', '_')

            product_fields = {
                'product_name': 'product_name',
                'product_code': 'product_code',
                'category': 'category',
                'unit': 'unit',
                'purchase_price': 'purchase_price',
                'selling_price': 'selling_price',
                'stock_quantity': 'stock_quantity',
                'min_stock_level': 'min_stock_level',
                'barcode': 'barcode',
                'tax_rate': 'tax_rate',
                'discount': 'discount',
                'expiry_date': 'expiry_date',
                'manufacturer': 'manufacturer',
                'supplier': 'supplier',
                'description': 'description',
                'is_active': 'is_active'
            }

            # Map file columns to model fields
            mapped_data = []
            for _, row in df.iterrows():
                product_data = {}
                for field, col_name in product_fields.items():
                    if col_name in row:
                        product_data[field] = row[col_name]
                
                # Set default values if not provided
                product_data.setdefault('stock_quantity', 0)
                product_data.setdefault('min_stock_level', 0)
                product_data.setdefault('tax_rate', 0)
                product_data.setdefault('discount', 0)
                product_data.setdefault('is_active', True)
                product_data['created_by'] = request.user.id
                
                mapped_data.append(product_data)

            # Validate and save products
            success_count = 0
            errors = []
            for data in mapped_data:
                serializer = ProductSerializer(data=data)
                if serializer.is_valid():
                    serializer.save()
                    success_count += 1
                else:
                    errors.append({
                        'row_data': data,
                        'errors': serializer.errors
                    })

            response = {
                'success_count': success_count,
                'error_count': len(errors),
                'errors': errors
            }

            if errors:
                return Response(response, status=status.HTTP_207_MULTI_STATUS)
            return Response(response, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class CreateSubscriptionAPIView(APIView):
    """Simulate a Razorpay payment and create subscription"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("plan_id")
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=404)

        # Simulate successful payment
        subscription = UserSubscription.objects.create(
            user=request.user,
            plan=plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(minutes=plan.duration_minutes),
            payment_id="FAKE_PAYMENT_ID_123",
            status="active"
        )

        request.user.plan_status = "active"
        request.user.save()

        return Response({
            "message": "Subscription created successfully",
            "plan": plan.name,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "status": subscription.status
        })


class CheckSubscriptionStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscriptions = request.user.subscriptions.all().order_by("-end_date")
        if not subscriptions.exists():
            return Response({"plan_status": "inactive"})

        latest = subscriptions.first()

        if timezone.now() > latest.end_date:
            latest.status = "expired"
            latest.save()
            request.user.plan_status = "expired"
            request.user.save()

        return Response({
            "plan_status": request.user.plan_status,
            "plan": latest.plan.name,
            "start_date": latest.start_date,
            "end_date": latest.end_date,
            "status": latest.status
        })
