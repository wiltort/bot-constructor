from celery import shared_task
from celery.utils.log import get_task_logger
from .models import Bot
from .bot_runner import start_bot_task, stop_bot_task, restart_bot_task
from django.conf import settings


logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, queue="bot_operations")
def start_bot(self, bot_id):
    """Celery задача для запуска бота"""
    try:
        bot = Bot.objects.get_by_id(bot_id)
        if not bot.is_active:
            logger.warning(f"Bot {bot.name} is not active, skipping start")
            return False
        logger.info(f"Startin bot {bot.name} (ID: {bot_id})")
        result = start_bot_task(bot_id)

        if result:
            logger.info(f"Bot {bot.name} started successfully")
            return True
        else:
            logger.error(f"Failed to start bot {bot.name}")
            raise self.retry(countdown=60)

    except Bot.DoesNotExist:
        logger.error(f"Bot with id {bot_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error starting bot {bot_id}: {e}", exc_info=True)
        self.retry(countdown=60, exc=e)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)
        else:
            logger.critical(f"Max retries exceeded for bot {bot_id}")
            return False


@shared_task(bind=True, max_retries=3, queue="bot_operations")
def stop_bot(self, bot_id):
    """Celery задача для остановки бота"""
    try:
        bot = Bot.objects.get_by_id(bot_id)

        # Останавливаем бота
        result = stop_bot_task(bot_id)

        if result:
            logger.info(f"Bot {bot.name} stopped successfully")
        else:
            logger.warning(f"Bot {bot.name} was not running or failed to stop")
            raise self.retry(countdown=60)
        return result

    except Bot.DoesNotExist as e:
        logger.error(f"Bot with id {bot_id} not found")
        raise self.retry(countdown=60, exc=e)
    except Exception as e:
        logger.error(f"Error stopping bot {bot_id}: {e}")
        raise self.retry(countdown=60, exc=e)


@shared_task(bind=True, max_retries=3, queue="bot_operations")
def restart_bot(self, bot_id):
    """Перезапуск бота"""
    try:
        result = restart_bot_task(bot_id)
        if result:
            logger.info(f"Bot {bot_id} restarted successfully")
            return True

        else:
            logger.error(f"Failed to restart bot {bot_id}")
            raise self.retry(countdown=60)

    except Exception as e:
        logger.error(f"Error restarting bot {bot_id}: {e}")
        raise self.retry(countdown=60, exc=e)


@shared_task
def check_bots_health():
    """Периодическая проверка здоровья ботов"""
    from .services import BotHealthChecker

    checker = BotHealthChecker()
    return checker.check_all_bots()

@shared_task
def start_all_bots_on_startup():
    from .services import BotService

    start = BotService()
    return start.start_all()

@shared_task
def cleanup_old_tasks():
    """
    Очистка старых завершенных задач из брокера.
    """
    try:
        import redis
        
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        count = 0
        
        old_keys = r.keys('celery-task-meta-*')
        if old_keys:
            count += r.delete(*old_keys)

        logger.info(f"Очищено задач: {count}")
        return {'cleaned': count, 'status': 'success'}
        
    except Exception as e:
        logger.error(f"Ошибка очистки задач: {e}")
        return {'status': 'error', 'error': str(e)}
