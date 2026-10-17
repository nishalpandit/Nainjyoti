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
    path('admin-dashboard/categories/', views.admin_categories, name='admin_categories'),
    path('admin-dashboard/categories/add/', views.admin_category_form, name='admin_category_add'),
    path('admin-dashboard/categories/<int:category_id>/edit/', views.admin_category_form, name='admin_category_edit'),

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
    # Vendor Category Endpoints (api/vendor/category/...)
    # =========================================================================
    path('api/vendor/category/list/', api_views.api_category_list, name='api_vendor_category_list'),
    path('api/vendor/category/create/', api_views.api_category_create, name='api_vendor_category_create'),
    path('api/vendor/category/detail/<int:category_id>/', api_views.api_category_detail, name='api_vendor_category_detail'),
    path('api/vendor/category/update/<int:category_id>/', api_views.api_category_update, name='api_vendor_category_update'),
    path('api/vendor/category/delete/<int:category_id>/', api_views.api_category_delete, name='api_vendor_category_delete'),
    path('api/vendor/category/tree/', api_views.api_category_tree, name='api_vendor_category_tree'),

    # =========================================================================
    # Admin Category Endpoints (api/admin/category/...)
    # =========================================================================
    path('api/admin/category/list/', api_views.api_category_list, name='api_admin_category_list'),
    path('api/admin/category/create/', api_views.api_category_create, name='api_admin_category_create'),
    path('api/admin/category/detail/<int:category_id>/', api_views.api_category_detail, name='api_admin_category_detail'),
    path('api/admin/category/update/<int:category_id>/', api_views.api_category_update, name='api_admin_category_update'),
    path('api/admin/category/delete/<int:category_id>/', api_views.api_category_delete, name='api_admin_category_delete'),
    path('api/admin/category/tree/', api_views.api_category_tree, name='api_admin_category_tree'),

    # =========================================================================
    # General / Direct Category Endpoints (api/category/...)
    # =========================================================================
    path('api/category/list/', api_views.api_category_list, name='api_category_list'),
    path('api/category/create/', api_views.api_category_create, name='api_category_create'),
    path('api/category/detail/<int:category_id>/', api_views.api_category_detail, name='api_category_detail'),
    path('api/category/update/<int:category_id>/', api_views.api_category_update, name='api_category_update'),
    path('api/category/delete/<int:category_id>/', api_views.api_category_delete, name='api_category_delete'),
    path('api/category/tree/', api_views.api_category_tree, name='api_category_tree'),

    # Legacy Category REST Aliases
    path('api/categories/', api_views.api_category_list_create, name='api_categories'),
    path('api/categories/tree/', api_views.api_category_tree, name='api_categories_tree_legacy'),
    path('api/categories/<int:category_id>/', api_views.api_category_detail_update_delete, name='api_categories_detail_legacy'),
    path('api/categories/<int:category_id>/update/', api_views.api_category_update, name='api_categories_update_legacy'),
    path('api/categories/<int:category_id>/delete/', api_views.api_category_delete, name='api_categories_delete_legacy'),
    path('api/categories/slug/<str:slug>/', api_views.api_category_detail, name='api_category_detail_by_slug'),

    # =========================================================================
    # Customer / User Web UI (Mobile-First Web Experience)
    # =========================================================================
    path('user/login/', user_views.user_login_view, name='user_login'),
    path('user/register/', user_views.user_register_view, name='user_register'),
    path('user/profile/', user_views.user_profile_view, name='user_profile'),
    path('user/logout/', user_views.user_logout_view, name='user_logout'),
]
