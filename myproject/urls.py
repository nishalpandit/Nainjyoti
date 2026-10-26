"""
URL configuration for myproject project.

Configured for both local development and cPanel / Apache production deployment.
Ensures static and media files are seamlessly served across all environments.
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

# Determine static serving directory (staticfiles if collected, else static source dir)
_static_dir = settings.STATIC_ROOT if (hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT and os.path.exists(settings.STATIC_ROOT)) else (
    settings.STATICFILES_DIRS[0] if (hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS) else settings.BASE_DIR / 'static'
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('nainjyoti.urls')),

    # Production & cPanel fallback handlers for uploaded media and static files
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': _static_dir}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=_static_dir)
