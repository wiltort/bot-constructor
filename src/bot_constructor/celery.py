import os
from celery import Celery
from celery.signals import worker_ready
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bot_constructor.settings")

app = Celery("bot_constructor")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.beat_schedule = {
    "check-bots-health-every-5-minutes": {
        "task": "bots.tasks.check_bots_health",
        "schedule": 300.0,
    },
    "cleanup-old-tasks-every-hour": {
        "task": "bots.tasks.cleanup_old_tasks",
        "schedule": 3600.0,
    },
}

app.conf.timezone = "UTC"
