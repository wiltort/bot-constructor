from celery import shared_task
from celery.utils.log import get_task_logger
import asyncio
from .models import Bot
from .bot_runner import start_bot_task, stop_bot_task

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, queue="bot_operations", default_retry_delay=300)
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
            self.retry(countdown=60 * 5)
            return False

    except Bot.DoesNotExist:
        logger.error(f"Bot with id {bot_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error starting bot {bot_id}: {e}", exc_info=True)
        self.retry(countdown=60 * 5, exc=e)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)
        else:
            logger.critical(f"Max retries exceeded for bot {bot_id}")
            return False


@shared_task
def stop_bot(bot_id):
    """Celery задача для остановки бота"""
    try:
        bot = Bot.objects.get(id=bot_id)

        # Останавливаем бота
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(stop_bot_task(bot_id))
        loop.close()

        if result:
            logger.info(f"Bot {bot.name} stopped successfully")
        else:
            logger.warning(f"Bot {bot.name} was not running or failed to stop")

        return result

    except Bot.DoesNotExist:
        logger.error(f"Bot with id {bot_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error stopping bot {bot_id}: {e}")
        return False


@shared_task
def restart_bot(bot_id):
    """Перезапуск бота"""
    try:
        stop_bot(bot_id)
        import time

        time.sleep(1)
        start_bot.delay(bot_id)
        return True

    except Exception as e:
        logger.error(f"Error restarting bot {bot_id}: {e}")
        return False


@shared_task
def start_all_bots():
    """Запуск всех активных ботов"""
    active_bots = Bot.objects.filter(is_active=True, is_running=False)
    results = []

    for bot in active_bots:
        result = start_bot.delay(bot.id)
        results.append((bot.id, result))

    return results


@shared_task
def stop_all_bots():
    """Остановка всех ботов"""
    running_bots = Bot.objects.filter(is_running=True)
    results = []

    for bot in running_bots:
        result = stop_bot.delay(bot.id)
        results.append((bot.id, result))

    return results


@shared_task
def check_bots_health():
    """Периодическая проверка здоровья ботов"""
    from .services import BotHealthChecker

    checker = BotHealthChecker()
    return checker.check_all_bots()
