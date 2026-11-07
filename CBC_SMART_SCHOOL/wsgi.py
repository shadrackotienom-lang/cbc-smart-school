import os
import sys

path = '/home/YOURUSERNAME/cbc-smart-school'
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CBC_SMART_SCHOOL.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()