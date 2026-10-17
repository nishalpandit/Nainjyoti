from django.urls import path
from . import views
from . import api_views
from . import user_views

urlpatterns = [
    # Public Vendor Portal & Unified Admin/Vendor Authentication
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login_page'),
    path('register/', views.vendor_register_view, name='vendor_register'),
    path('vendor-register/', views.vendor_register_view, name='vendor_register_alias'),
    path('status/', views.vendor_status_view, name='vendor_status'),
    path('status/<str:vendor_code>/', views.vendor_status_view, name='vendor_status'),
    path('status-lookup/', views.vendor_status_lookup_view, name='vendor_status_lookup'),
    path('logout/', views.logout_view, name='logout'),

    # Admin Protected Dashboards
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/vendor-approval/', views.admin_vendor_approval, name='admin_vendor_approval'),
    path('admin-dashboard/vendor/<int:vendor_id>/kyc/', views.admin_vendor_kyc_detail, name='admin_vendor_kyc_detail'),

    # Vendor Protected Dashboard
    path('vendor-dashboard/', views.vendor_dashboard, name='vendor_dashboard'),

    # =========================================================================
    # Customer / Mobile App REST APIs
    # =========================================================================
    path('api/user/send-otp/', api_views.api_send_otp, name='api_send_otp'),
    path('api/user/verify-otp-login/', api_views.api_verify_otp_login, name='api_verify_otp_login'),
    path('api/user/register/', api_views.api_user_register, name='api_user_register'),
    path('api/user/profile/', api_views.api_user_profile, name='api_user_profile'),
    path('api/user/logout/', api_views.api_user_logout, name='api_user_logout'),

    # =========================================================================
    # Vendor / Merchant REST APIs
    # =========================================================================
    path('api/vendor/register/', api_views.api_vendor_register, name='api_vendor_register'),
    path('api/vendor/login/', api_views.api_vendor_login, name='api_vendor_login'),
    path('api/vendor/profile/', api_views.api_vendor_profile, name='api_vendor_profile'),
    path('api/vendor/profile/change-password/', api_views.api_vendor_change_password, name='api_vendor_change_password'),
    path('api/vendor/status/', api_views.api_vendor_status_lookup, name='api_vendor_status_lookup'),
    path('api/vendor/logout/', api_views.api_vendor_logout, name='api_vendor_logout'),

    # =========================================================================
    # Customer / User Web UI (Mobile-First Web Experience)
    # =========================================================================
    path('user/login/', user_views.user_login_view, name='user_login'),
    path('user/register/', user_views.user_register_view, name='user_register'),
    path('user/profile/', user_views.user_profile_view, name='user_profile'),
    path('user/logout/', user_views.user_logout_view, name='user_logout'),
]
