from django.urls import path
from . import views
from . import api_views
from . import user_views
from . import vendor_views

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
    path('admin-dashboard/customers/', views.admin_customers, name='admin_customers'),
    path('admin-dashboard/addresses/', views.admin_addresses, name='admin_addresses'),
    path('admin-dashboard/customers/<int:customer_id>/toggle-status/', views.admin_customer_toggle_status, name='admin_customer_toggle_status'),
    path('admin-dashboard/customers/<int:customer_id>/detail/', views.admin_customer_detail, name='admin_customer_detail'),
    path('admin-dashboard/customers/<int:customer_id>/edit/', views.admin_customer_edit, name='admin_customer_edit'),
    path('admin-dashboard/vendors/', views.admin_vendors, name='admin_vendors'),
    path('admin-dashboard/vendor-approval/', views.admin_vendor_approval, name='admin_vendor_approval'),
    path('admin-dashboard/vendor/<int:vendor_id>/kyc/', views.admin_vendor_kyc_detail, name='admin_vendor_kyc_detail'),
    path('admin-dashboard/categories/', views.admin_categories, name='admin_categories'),
    path('admin-dashboard/categories/add/', views.admin_category_form, name='admin_category_add'),
    path('admin-dashboard/categories/<int:category_id>/edit/', views.admin_category_form, name='admin_category_edit'),
    path('admin-dashboard/categories/<int:category_id>/toggle-status/', views.admin_category_toggle_status, name='admin_category_toggle_status'),
    path('admin-dashboard/products/', views.admin_products, name='admin_products'),
    path('admin-dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('admin-dashboard/payments/', views.admin_payments, name='admin_payments'),
    path('admin-dashboard/reports/', views.admin_reports, name='admin_reports'),
    path('admin-dashboard/settings/', views.admin_settings, name='admin_settings'),

    # =========================================================================
    # Vendor Web Dashboard (Full Dynamic Portal)
    # =========================================================================
    path('vendor-dashboard/', vendor_views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor-dashboard/products/', vendor_views.vendor_products, name='vendor_products'),
    path('vendor-dashboard/products/add/', vendor_views.vendor_product_add, name='vendor_product_add'),
    path('vendor-dashboard/products/<int:product_id>/edit/', vendor_views.vendor_product_edit, name='vendor_product_edit'),
    path('vendor-dashboard/products/<int:product_id>/delete/', vendor_views.vendor_product_delete, name='vendor_product_delete'),
    path('vendor-dashboard/orders/', vendor_views.vendor_orders, name='vendor_orders'),
    path('vendor-dashboard/orders/<int:order_id>/', vendor_views.vendor_order_detail, name='vendor_order_detail'),
    path('vendor-dashboard/orders/<int:order_id>/status/', vendor_views.vendor_order_update_status, name='vendor_order_update_status'),
    path('vendor-dashboard/inventory/', vendor_views.vendor_inventory, name='vendor_inventory'),
    path('vendor-dashboard/inventory/adjust/<int:product_id>/', vendor_views.vendor_stock_adjust, name='vendor_stock_adjust'),
    path('vendor-dashboard/earnings/', vendor_views.vendor_earnings, name='vendor_earnings'),
    path('vendor-dashboard/withdrawals/', vendor_views.vendor_withdrawals, name='vendor_withdrawals'),
    path('vendor-dashboard/withdrawals/request/', vendor_views.vendor_payout_request, name='vendor_payout_request'),
    path('vendor-dashboard/settings/', vendor_views.vendor_settings, name='vendor_settings'),

    # =========================================================================
    # Customer / Mobile App REST APIs
    # =========================================================================
    path('api/user/send-otp/', api_views.api_send_otp, name='api_send_otp'),
    path('api/user/verify-otp-login/', api_views.api_verify_otp_login, name='api_verify_otp_login'),
    path('api/user/register/', api_views.api_user_register, name='api_user_register'),
    path('api/user/login/', api_views.api_user_login, name='api_user_login'),
    path('api/user/status/', api_views.api_user_status, name='api_user_status'),
    path('api/user/profile/', api_views.api_user_profile, name='api_user_profile'),
    path('api/user/profile/update/', api_views.api_user_profile_update, name='api_user_profile_update'),
    path('api/user/profile/photo/', api_views.api_user_profile_photo, name='api_user_profile_photo'),
    path('api/user/logout/', api_views.api_user_logout, name='api_user_logout'),
    path('api/user/address/create/', api_views.api_user_address_create, name='api_user_address_create'),
    path('api/user/address/list/', api_views.api_user_address_list, name='api_user_address_list'),
    path('api/user/address/detail/<int:address_id>/', api_views.api_user_address_detail, name='api_user_address_detail'),
    path('api/user/address/update/<int:address_id>/', api_views.api_user_address_update, name='api_user_address_update'),
    path('api/user/address/set-default/<int:address_id>/', api_views.api_user_address_set_default, name='api_user_address_set_default'),
    path('api/user/address/delete/<int:address_id>/', api_views.api_user_address_delete, name='api_user_address_delete'),
    path('api/user/categories/', api_views.api_user_category_list, name='api_user_category_list'),
    path('api/user/category/list/', api_views.api_user_category_list, name='api_user_category_list_alias'),
    path('api/user/categories/<int:category_id>/', api_views.api_user_category_detail, name='api_user_category_detail'),
    path('api/user/category/detail/<int:category_id>/', api_views.api_user_category_detail, name='api_user_category_detail_alias'),
    path('api/user/categories/<int:category_id>/products/', api_views.api_user_category_products, name='api_user_category_products'),
    path('api/user/category/products/<int:category_id>/', api_views.api_user_category_products, name='api_user_category_products_alias'),
    path('api/user/products/search/', api_views.api_product_search, name='api_user_product_search'),
    path('api/user/products/<int:product_id>/', api_views.api_user_product_detail, name='api_user_product_detail'),
    path('api/user/product/detail/<int:product_id>/', api_views.api_user_product_detail, name='api_user_product_detail_alias'),
    path('api/user/products/<int:product_id>/variants/', api_views.api_user_product_variants, name='api_user_product_variants'),
    path('api/user/variants/<int:variant_id>/', api_views.api_user_variant_detail, name='api_user_variant_detail'),
    path('api/products/<int:product_id>/', api_views.api_user_product_detail, name='api_product_detail_alias'),
    path('api/products/search/', api_views.api_product_search, name='api_product_search_alias'),

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
    # Vendor Product Management Endpoints (api/vendor/product/...)
    # =========================================================================
    path('api/vendor/product/list/', api_views.api_product_list, name='api_vendor_product_list'),
    path('api/vendor/product/create/', api_views.api_product_create, name='api_vendor_product_create'),
    path('api/vendor/product/detail/<int:product_id>/', api_views.api_product_detail, name='api_vendor_product_detail'),
    path('api/vendor/product/update/<int:product_id>/', api_views.api_product_update, name='api_vendor_product_update'),
    path('api/vendor/product/delete/<int:product_id>/', api_views.api_product_delete, name='api_vendor_product_delete'),
    path('api/vendor/products/<int:product_id>/variants/', api_views.api_product_variant_list, name='api_vendor_product_variant_list'),
    path('api/vendor/products/<int:product_id>/variants/create/', api_views.api_product_variant_create, name='api_vendor_product_variant_create'),
    path('api/vendor/variants/<int:variant_id>/', api_views.api_product_variant_detail, name='api_vendor_product_variant_detail'),
    path('api/vendor/variants/<int:variant_id>/update/', api_views.api_product_variant_update, name='api_vendor_product_variant_update'),
    path('api/vendor/variants/<int:variant_id>/delete/', api_views.api_product_variant_delete, name='api_vendor_product_variant_delete'),

    # =========================================================================
    # Admin Product Management Endpoints (api/admin/product/...)
    # =========================================================================
    path('api/admin/product/list/', api_views.api_product_list, name='api_admin_product_list'),
    path('api/admin/product/create/', api_views.api_product_create, name='api_admin_product_create'),
    path('api/admin/product/detail/<int:product_id>/', api_views.api_product_detail, name='api_admin_product_detail'),
    path('api/admin/product/update/<int:product_id>/', api_views.api_product_update, name='api_admin_product_update'),
    path('api/admin/product/delete/<int:product_id>/', api_views.api_product_delete, name='api_admin_product_delete'),
    path('api/admin/products/<int:product_id>/variants/', api_views.api_product_variant_list, name='api_admin_product_variant_list'),
    path('api/admin/products/<int:product_id>/variants/create/', api_views.api_product_variant_create, name='api_admin_product_variant_create'),
    path('api/admin/variants/<int:variant_id>/', api_views.api_product_variant_detail, name='api_admin_product_variant_detail'),
    path('api/admin/variants/<int:variant_id>/update/', api_views.api_product_variant_update, name='api_admin_product_variant_update'),
    path('api/admin/variants/<int:variant_id>/delete/', api_views.api_product_variant_delete, name='api_admin_product_variant_delete'),

    # =========================================================================
    # General / Direct Product Endpoints (api/product/...)
    # =========================================================================
    path('api/product/list/', api_views.api_product_list, name='api_product_list'),
    path('api/product/create/', api_views.api_product_create, name='api_product_create'),
    path('api/product/detail/<int:product_id>/', api_views.api_product_detail, name='api_product_detail'),
    path('api/product/update/<int:product_id>/', api_views.api_product_update, name='api_product_update'),
    path('api/product/delete/<int:product_id>/', api_views.api_product_delete, name='api_product_delete'),

    # Legacy / REST Product Aliases
    path('api/products/', api_views.api_product_list_create, name='api_products_list_create'),
    path('api/products/<int:product_id>/', api_views.api_product_detail_update_delete, name='api_products_detail'),
    path('api/products/<int:product_id>/update/', api_views.api_product_update, name='api_products_update_legacy'),
    path('api/products/<int:product_id>/delete/', api_views.api_product_delete, name='api_products_delete_legacy'),

    # =========================================================================
    # Vendor Stock / Inventory Management Endpoints (api/vendor/stock/...)
    # =========================================================================
    path('api/vendor/stock/summary/', api_views.api_stock_summary, name='api_vendor_stock_summary'),
    path('api/vendor/stock/list/', api_views.api_stock_list, name='api_vendor_stock_list'),
    path('api/vendor/stock/update/<int:product_id>/', api_views.api_stock_update, name='api_vendor_stock_update'),
    path('api/vendor/stock/logs/', api_views.api_stock_logs, name='api_vendor_stock_logs_all'),
    path('api/vendor/stock/logs/<int:product_id>/', api_views.api_stock_logs, name='api_vendor_stock_logs_product'),

    # =========================================================================
    # Admin Stock Aliases (api/admin/stock/...)
    # =========================================================================
    path('api/admin/stock/summary/', api_views.api_stock_summary, name='api_admin_stock_summary'),
    path('api/admin/stock/list/', api_views.api_stock_list, name='api_admin_stock_list'),
    path('api/admin/stock/update/<int:product_id>/', api_views.api_stock_update, name='api_admin_stock_update'),
    path('api/admin/stock/logs/', api_views.api_stock_logs, name='api_admin_stock_logs_all'),
    path('api/admin/stock/logs/<int:product_id>/', api_views.api_stock_logs, name='api_admin_stock_logs_product'),

    # =========================================================================
    # General Stock Endpoints (api/stock/...)
    # =========================================================================
    path('api/stock/summary/', api_views.api_stock_summary, name='api_stock_summary'),
    path('api/stock/list/', api_views.api_stock_list, name='api_stock_list'),
    path('api/stock/update/<int:product_id>/', api_views.api_stock_update, name='api_stock_update'),
    path('api/stock/logs/', api_views.api_stock_logs, name='api_stock_logs_all'),
    path('api/stock/logs/<int:product_id>/', api_views.api_stock_logs, name='api_stock_logs_product'),

    # =========================================================================
    # Vendor Orders & Customer Management Endpoints (api/vendor/orders/...)
    # =========================================================================
    path('api/vendor/orders/', api_views.api_vendor_orders, name='api_vendor_orders_list'),
    path('api/vendor/orders/<str:order_id>/', api_views.api_vendor_order_detail, name='api_vendor_order_detail'),
    path('api/vendor/orders/<str:order_id>/status/', api_views.api_vendor_order_status_update, name='api_vendor_order_status_update'),

    # =========================================================================
    # Vendor Sales & Earnings Endpoints
    # =========================================================================
    path('api/vendor/sales/overview/', api_views.api_vendor_sales_overview, name='api_vendor_sales_overview'),
    path('api/vendor/earnings/overview/', api_views.api_vendor_earnings_overview, name='api_vendor_earnings_overview'),

    # =========================================================================
    # Vendor Withdrawal / Settlement Endpoints (api/vendor/payout/...)
    # =========================================================================
    path('api/vendor/payout/request/', api_views.api_vendor_payout_request, name='api_vendor_payout_request'),
    path('api/vendor/payout/history/', api_views.api_vendor_payout_history, name='api_vendor_payout_history'),
    path('api/vendor/payout/detail/<str:payout_id>/', api_views.api_vendor_payout_detail, name='api_vendor_payout_detail'),


    # =========================================================================
    # Customer / User Web UI (Mobile-First Web Experience)
    # =========================================================================
    path('user/login/', user_views.user_login_view, name='user_login'),
    path('user/register/', user_views.user_register_view, name='user_register'),
    path('user/profile/', user_views.user_profile_view, name='user_profile'),
    path('user/logout/', user_views.user_logout_view, name='user_logout'),
]
