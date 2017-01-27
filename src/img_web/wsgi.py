import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "img_web.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
