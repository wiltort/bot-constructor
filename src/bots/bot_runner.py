import asyncio
import logging
import threading
from telegram.ext import Application
from django.utils import timezone
from .models import Bot
from openai import OpenAI
from .handlers import HandlerManager
from asgiref.sync import sync_to_async


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
        self._polling_thread = None
        self.history = dict()
        self.ai_client = None
        self.ai_model = None

    def initialize(self) -> bool:
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
                handler_converter = handler_manager.get_converter(scenario)(scenario)
                handlers = handler_converter.create_handlers(bot_runner=self)
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

    def _save_status(self, is_running, last_started=None, last_stopped=None):
        """Сохранение статуса бота"""
        update_fields = ["is_running"]
        self.bot_instance.is_running = is_running

        if last_started:
            self.bot_instance.last_started = last_started
            update_fields.append("last_started")
        if last_stopped:
            self.bot_instance.last_stopped = last_stopped
            update_fields.append("last_stopped")

        self.bot_instance.save(update_fields=update_fields)

    def _polling_worker(self):
        """
        Рабочая функция, которая запускается в отдельном потоке
        и управляет своим собственным event loop.
        """
        try:
            # Создаем новый event loop для этого потока
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Запускаем асинхронную функцию polling в этом loop
            self.loop.run_until_complete(self._run_polling_async())
        except Exception as e:
            logger.error(f"Polling error in thread: {e}", exc_info=True)
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            self.is_running = False
            self._save_status(False)

    async def _run_polling_async(self):
        """Асинхронный запуск polling с ручным управлением"""
        try:
            if not self.application:
                if not await sync_to_async(self.initialize)():
                    logger.error("Failed to initialize application")
                    return
            logger.info("Application initialization")
            await self.application.initialize()

            await self.application.start()
            await self.application.updater.start_polling()

            logger.info("Bot polling started")

            while self.application.running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Bot polling cancelled")
        except Exception as e:
            logger.error(f"Polling error for bot {e}")
        finally:
            try:
                if self.application:
                    if self.application.updater.running:
                        await asyncio.wait_for(
                            self.application.updater.stop(),
                            timeout=5.0
                        )
                    if self.application.running:
                        await asyncio.wait_for(
                            self.application.stop(),
                            timeout=5.0
                        )
                    await asyncio.wait_for(
                        self.application.shutdown(),
                        timeout=5.0
                    )
            except Exception as e:
                    logger.error(f"Error during shutdown: {e}")

    def start(self) -> bool:
        """
        Запускает Telegram-бота и отмечает его как активного.
        :return: True если успешно запущен, иначе False
        """
        if self.is_running:
            logger.warning(f"Bot {self.bot_instance.name} is already running")
            self._save_status(True)
            return False
        
        if self._polling_thread and self._polling_thread.is_alive():
            logger.warning("Previous bot instance is still stopping, waiting...")
            self._polling_thread.join(timeout=3.0)
            if self._polling_thread.is_alive():
                logger.error("Previous bot instance is still running, cannot start new one")
                return False
        try:
            self.application = None
            self.loop = None
            self._polling_thread = threading.Thread(
                target=self._polling_worker,
                name=f"BotPolling-{self.bot_instance.id}-{timezone.now().timestamp()}",
                daemon=True,
            )
            self._polling_thread.start()
            self.is_running = True
            self._save_status(True, last_started=timezone.now())
            logger.info(
                f"Bot {self.bot_instance.name} started successfully in thread {self._polling_thread.name}"
            )
            return True

        except Exception as e:
            logger.error(f"Error starting bot {self.bot_instance.name}: {e}")
            self.is_running = False
            self._save_status(False)
            return False

    def stop(self) -> bool:
        """
        Останавливает работу Telegram-бота и записывает событие в БД.
        :return: True если успешно остановлен, иначе False
        """
        if not self.is_running:
            logger.warning(f"Bot {self.bot_instance.name} is not running")
            self._save_status(False)
            return False

        try:
            self.is_running = False
            try:
                stop_future = asyncio.run_coroutine_threadsafe(
                    self._stop_async(), self.loop
                )
                stop_future.result(timeout=10.0)
                logger.info("Application stopped via event loop")
            except Exception as e:
                logger.warning(f"Could not stop via event loop: {e}")
                if self.loop and self.loop.is_running:
                    self.loop.call_soon_threadsafe(self.loop.stop)

            if self._polling_thread and self._polling_thread.is_alive():
                self._polling_thread.join(timeout=5.0)
                if self._polling_thread.is_alive():
                    logger.warning("Polling thread still alive after timeout")
                else:
                    logger.info("Polling thread closed")

            self.application = None
            self.loop = None

            self._save_status(False, last_stopped=timezone.now())

            logger.info(f"Bot {self.bot_instance.name} stopped succesfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping bot {self.bot_instance.name}: {e}")
            self.is_running = False
            self._save_status(False, last_stopped=timezone.now())
            return False

    def restart(self):
        """
        Перезапускает Telegram-бота (остановка с новым запуском).
        Можно использовать для применения обновленных настроек или сценария.
        """
        self.stop()
        self.bot_instance.refresh_from_db()
        return self.start()

    async def _stop_async(self):
        """Асинхронная процедура остановки."""
        # Эта корутина будет запущена в целевом event loop
        logger.info("Async stopping")
        if self.application:
            logger.info("app is found")
            if self.application.updater.running:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("done")


# Глобальный словарь для хранения запущенных ботов
running_bots = {}


def start_bot_task(bot_id):
    """
    Запуск Telegram-бота по id.
    :param bot_id: int, id бота
    :return: True если успешно, иначе False
    """
    existing_runner = running_bots.get(bot_id)
    if existing_runner and existing_runner.is_running:
        logger.warning(f"Start requested for bot {bot_id}, but it's already running.")
        return False
    try:
        bot = Bot.objects.get_by_id(bot_id)
        if not bot or not bot.is_active:
            raise BotStartingError("Bot is not active or not found")
        runner = DjangoBotRunner(bot)
        running_bots[bot_id] = runner
        return runner.start()
    except Exception as e:
        logger.error(f"Error in start_bot_task for bot {bot_id}: {e}")
        existing_runner = running_bots.get(bot_id)
        if existing_runner:
            running_bots.pop(existing_runner)
        return False


def stop_bot_task(bot_id):
    """
    Задача остановки Telegram-бота по id.
    :param bot_id: int
    :return: True если успешно, иначе False
    """
    try:
        runner = running_bots.get(bot_id)
        if runner:
            logger.info("Runner found")
            result = runner.stop()
            running_bots.pop(bot_id, None)
            return result
        logger.warning("Runner not found")
        bot = Bot.objects.get_by_id(bot_id)
        if bot:
            bot.is_running = False
            bot.save(update_fields=['is_running'])
        return False
    except Exception as e:
        logger.error(f"Error in stop_bot_task for bot {bot_id}: {e}")
        return False


def restart_bot_task(bot_id):
    """
    Задача перезагрузки Telegram-бота по id.
    :param bot_id: int
    :return: True если успешно, иначе False
    """
    try:
        runner = running_bots.get(bot_id)
        if not runner:
            logger.warning(f"No runner found for bot {bot_id}, starting new one")
            return start_bot_task(bot_id)
        
        # Сохраняем ссылку на старого runner
        old_runner = runner
        
        # Создаем нового runner с обновленными данными
        bot = Bot.objects.get_by_id(bot_id)
        new_runner = DjangoBotRunner(bot)
        running_bots[bot_id] = new_runner
        
        # Останавливаем старого runner
        stop_result = old_runner.stop()
        
        if not stop_result:
            logger.warning(f"Failed to stop old runner for bot {bot_id}")
        
        # Даем время на остановку
        import time
        time.sleep(2)
        
        # Запускаем нового runner
        start_result = new_runner.start()
        
        if start_result:
            logger.info(f"Bot {bot_id} restarted successfully")
            return True
        else:
            logger.error(f"Failed to restart bot {bot_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error in restart_bot_task for bot {bot_id}: {e}")
        return False