import os
from dotenv import load_dotenv
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:    
    load_dotenv()
except ImportError:
    pass

application = get_wsgi_application()
