import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bot_constructor.settings')

app = Celery('bot_constructor')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
