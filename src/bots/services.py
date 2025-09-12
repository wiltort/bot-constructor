from celery.result import AsyncResult
import requests
from .models import Bot
from .tasks import start_bot, stop_bot, restart_bot
import logging

logger = logging.getLogger(__name__)


class BotService:
    """Сервис для управления ботами"""

    @staticmethod
    def check_celery_available():
        """Проверка доступности Celery"""
        try:
            # Простая проверка подключения к брокеру
            from celery import current_app
            insp = current_app.control.inspect()
            if insp.ping():
                return True
            return False
        except Exception as e:
            logger.error(f"Celery check failed: {e}")
            return False

    @staticmethod
    def start_bot(bot_id):
        """Запустить бота"""
        if not BotService.check_celery_available():
            logger.error("Celery is not available. Cannot start bot.")
            return None
        try:
            task = start_bot.delay(bot_id)
            logger.info(f"Start task created for bot {bot_id}: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Error starting bot {bot_id}: {e}")
            return None

    @staticmethod
    def stop_bot(bot_id):
        """Остановить бота"""
        try:
            task = stop_bot.delay(bot_id)
            return task.id
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {e}")
            return None

    @staticmethod
    def restart_bot(bot_id):
        """Перезапустить бота"""
        try:
            task = restart_bot.delay(bot_id)
            return task.id
        except Exception as e:
            logger.error(f"Error restarting bot {bot_id}: {e}")
            return None

    @staticmethod
    def get_task_status(task_id):
        """Получить статус задачи"""
        try:
            task = AsyncResult(task_id)
            return {
                "status": task.status,
                "result": task.result,
                "ready": task.ready(),
                "failed": task.failed(),
            }
        except Exception as e:
            logger.error(f"Error getting task status {task_id}: {e}")
            return None


class BotHealthChecker:
    """Проверка здоровья ботов"""

    def check_bot_health(self, bot_id):
        """Проверить здоровье конкретного бота"""
        bot = Bot.objects.get(id=bot_id)
        token = bot.telegram_token
        url = f"https://api.telegram.org/bot{token}/getMe"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200 and response.json().get("ok"):
                return {"status": "healthy", "bot_id": bot_id}
            else:
                return {
                    "status": "unreachable",
                    "bot_id": bot_id,
                    "error": response.json(),
                }
        except requests.RequestException as e:
            return {"status": "unreachable", "bot_id": bot_id, "error": str(e)}

    def check_all_bots(self):
        """Проверить всех ботов"""
        results = {}
        for bot in Bot.objects.filter(is_active=True):
            results[bot.id] = self.check_bot_health(bot.id)
        return results
