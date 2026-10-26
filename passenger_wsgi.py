"""
Phusion Passenger WSGI entry point for cPanel deployment.
cPanel's 'Setup Python App' (Passenger) loads this file to start the Django application.
"""
import os
import sys

# Add application root directory to Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Load Django WSGI application handler
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
