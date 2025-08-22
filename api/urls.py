from django.urls import path,include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'user',UserViewSet,basename='users')
router.register(r'products', ProductViewSet)
router.register(r'customers', CustomerViewSet,basename='add-customers')

router.register(r'vendors', AddVendorViewSet, basename='vendor')

router.register(r'bill-settings', BillSettingsViewSet, basename='bill-settings')

router.register(r'backups', DataBackupViewSet, basename='backups')

router.register(r'users', UsersViewSet, basename='user')   # admin can see

router.register(r'sales', SaleViewSet, basename='sales')    # sales

router.register(r'users-list', UserViewSetDetail, basename='users-sales')

router.register(r'tickets', TicketViewSet, basename='ticket')


urlpatterns = [
    path('register/',RegisterView.as_view(),name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('',include(router.urls)),

    path('api/bill-settings/mine/', BillSettingsViewSet.as_view({'get': 'mine', 'put': 'mine', 'patch': 'mine'})),

    path('import-products/', ProductImportView.as_view(), name='import-products'),

    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),

    path('check-email/', CheckEmailView.as_view(), name='check-email'),
]