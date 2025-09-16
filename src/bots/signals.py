from celery.signals import worker_ready


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    try:
        from bots.tasks import start_all_bots_on_startup
        start_all_bots_on_startup.delay()
    except Exception as e:
        print(e)
