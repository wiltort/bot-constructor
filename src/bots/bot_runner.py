import logging
from telegram.ext import Application
from django.utils import timezone
from .models import Bot
from openai import OpenAI
from .handlers import HandlerManager

logger = logging.getLogger(__name__)


class HandlerInitException(Exception):
    """Исключение при создании хэндлеров."""

    pass


class BotStartingError(Exception):
    """Исключение при запуске бота."""

    pass


class DjangoBotRunner:
    """
    Менеджер, контролирующий жизненный цикл Telegram-бота.
    Отвечает за инициализацию, запуск и остановку соответствующего Telegram-приложения.
    """

    def __init__(self, bot_instance: Bot):
        """
        :param bot_instance: объект бота из БД
        """
        self.bot_instance = bot_instance
        self.application = None
        self.is_running = False
        self.loop = None
        self.history = []
        self.ai_client = None
        self.ai_model = None

    async def initialize(self) -> bool:
        """
        Инициализация приложения Telegram и OpenAI-клиента.
        Добавляет обработчики согласно сценарию.
        :return: True если успешно, иначе False
        """
        try:
            self.ai_model = self.bot_instance.ai_model
            self.ai_client = OpenAI(
                api_key=self.bot_instance.gpt_api_key,
                base_url=self.bot_instance.gpt_api_url or None,
            )
            self.application = (
                Application.builder().token(self.bot_instance.telegram_token).build()
            )
            scenario = self.bot_instance.current_scenario
            if scenario:
                handler_manager = HandlerManager()
                handler_converter = handler_manager.get_converter(scenario)
                handlers = handler_converter.create_handlers(self)
                if not handlers:
                    raise HandlerInitException(
                        "Error creating handlers (no one has created)"
                    )
                for handler in handlers:
                    self.application.add_handler(handler)
            else:
                raise HandlerInitException("Scenario not found")
            return True
        except Exception as e:
            logger.error(f"Error initializing bot {self.bot_instance.name}: {e}")
            return False

    async def start(self) -> bool:
        """
        Запускает Telegram-бота и отмечает его как активного.
        :return: True если успешно запущен, иначе False
        """
        if self.is_running:
            logger.warning(f"Bot {self.bot_instance.name} is already running")
            self.bot_instance.is_running = True
            self.bot_instance.save(update_fields=["is_running"])
            return False

        if not self.application:
            if not await self.initialize():
                self.is_running = False
                self.bot_instance.is_running = False
                self.bot_instance.save(update_fields=["is_running"])
                return False

        try:
            await self.application.run_polling()

            self.is_running = True
            self.bot_instance.is_running = True
            self.bot_instance.last_started = timezone.now()
            self.bot_instance.save(update_fields=["is_running", "last_started"])

            logger.info(f"Bot {self.bot_instance.name} started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting bot {self.bot_instance.name}: {e}")
            self.is_running = False
            self.bot_instance.is_running = False
            self.bot_instance.save(update_fields=["is_running"])
            return False

    async def stop(self) -> bool:
        """
        Останавливает работу Telegram-бота и записывает событие в БД.
        :return: True если успешно остановлен, иначе False
        """
        if not self.is_running:
            logger.warning(f"Bot {self.bot_instance.name} is not running")
            self.bot_instance.is_running = False
            self.bot_instance.save(update_fields=["is_running"])
            return False

        try:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()
                self.application = None

            self.is_running = False
            self.bot_instance.is_running = False
            self.bot_instance.last_stopped = timezone.now()
            self.bot_instance.save(update_fields=["is_running", "last_stopped"])

            logger.info(f"Bot {self.bot_instance.name} stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping bot {self.bot_instance.name}: {e}")
            return False

    async def restart(self):
        """
        Перезапускает Telegram-бота (остановка с новым запуском).
        Можно использовать для применения обновленных настроек или сценария.
        """
        await self.stop()
        self.bot_instance.refresh_from_db()
        return await self.start()


# Глобальный словарь для хранения запущенных ботов
running_bots = {}


def get_bot_runner(bot_id):
    """
    Получить runner для бота по его ID.
    :param bot_id: int, id бота
    :return: DjangoBotRunner или None
    """
    return running_bots.get(bot_id)


async def start_bot_task(bot_id):
    """
    Асинхронный запуск Telegram-бота по id.
    :param bot_id: int, id бота
    :return: True если успешно, иначе False
    """
    existing_runner = running_bots.get(bot_id)
    if existing_runner and existing_runner.is_running:
        logger.warning(f"Start requested for bot {bot_id}, but it's already running.")
        return False
    try:
        bot = Bot.objects.get(id=bot_id)
        if not bot.is_active:
            raise BotStartingError("Bot is not active")
        runner = DjangoBotRunner(bot)
        running_bots[bot_id] = runner
        return await runner.start()
    except Exception as e:
        logger.error(f"Error in start_bot_task for bot {bot_id}: {e}")
        return False


async def stop_bot_task(bot_id):
    """
    Асинхронная задача остановки Telegram-бота по id.
    :param bot_id: int
    :return: True если успешно, иначе False
    """
    try:
        runner = running_bots.get(bot_id)
        if runner:
            result = await runner.stop()
            running_bots.pop(bot_id, None)
            return result
        return False
    except Exception as e:
        logger.error(f"Error in stop_bot_task for bot {bot_id}: {e}")
        return False
