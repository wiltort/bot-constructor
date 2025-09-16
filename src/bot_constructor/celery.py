import os
from celery import Celery
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
    "start-bots-on-startup": {
        "task": "bots.tasks.start_all_bots_on_startup",
        "schedule": 10,
        "options": {
            "expires": 20,
            "one_off": True,
        },
    },
}

app.conf.timezone = "UTC"
