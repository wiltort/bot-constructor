from abc import ABC, abstractmethod
import logging
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from .models import Scenario, Step


logger = logging.getLogger(__name__)


class HandlerManager:
    """
    Менеджер для хранения и выбора подходящего конвертера обработчиков
    для разных типов сценариев.
    В качестве ключа используется строка-ярлык типа сценария.
    """

    _converters = {}

    @classmethod
    def telegram_handler(cls, keyword: str):
        """
        Декоратор для регистрации класса-конвертера по ключу.
        Можно использовать для расширения типов сценариев.
        """

        def wrapper(converter_cls):
            cls._converters[keyword] = converter_cls
            return converter_cls

        return wrapper

    @classmethod
    def get_converter(cls, scenario: Scenario):
        """
        Возвращает подходящий класс конвертера для заданного сценария.
        По умолчанию используется ConversationConverter.
        """
        converter = cls._converters.get(
            Scenario.ScenarioType(scenario.scenario_type).label,
            ConversationConverter,
        )
        return converter


class AbstractConverter(ABC):
    """
    Абстрактный конвертер сценариев в обработчики Telegram.
    Отвечает за подготовку списка хэндлеров.
    """

    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    @staticmethod
    async def send_split_message(update: Update, text: str, max_length: int = 4096):
        """
        Отправляет сообщение по частям, если оно превышает лимит Telegram.

        :param update: Объект Update телеграма
        :param text: Сообщение для отправки
        :param max_length: Максимально допустимая длина текста
        """
        if len(text) <= max_length:
            await update.message.reply_text(text)
            return
        parts = []
        while text:
            if len(text) > max_length:
                # Ищем место для разбивки (последний пробел)
                split_index = text[:max_length].rfind("\n")
                if split_index == -1:
                    split_index = text[:max_length].rfind(" ")
                if split_index == -1:
                    split_index = max_length
                parts.append(text[:split_index])
                text = text[split_index:].lstrip()
            else:
                parts.append(text)
                break
        for part in parts:
            await update.message.reply_text(part)

    @abstractmethod
    def create_handlers(self, bot_runner):
        """
        Метод для создания структуры ConversationHandler.
        Должен быть реализован в дочерних конвертерах.
        """
        raise NotImplementedError


@HandlerManager.telegram_handler(keyword=Scenario.ScenarioType.CONVERSATION.label)
class ConversationConverter(AbstractConverter):
    """
    Конвертер для сценариев типа "Conversation".
    Собирает состояния, точки входа, состояния и fallback-и для ConversationHandler.
    """

    def __init__(self, scenario):
        super().__init__(scenario)
        self.states = {}
        self._state_index = -1

    def add_state(self, state: str):
        """
        Добавляет новое состояние (state) в словарь состояний,
        если оно еще не добавлено.
        """
        if state not in self.states:
            self._state_index += 1
            self.states[state] = self._state_index
            return True
        return False

    def create_handlers(self, bot_runner):
        """
        Строит список ConversationHandler-ов на основании шагов сценария.

        :param bot_runner: Экземпляр runner-а бота (context)
        :return: Список ConversationHandler
        """
        steps = Step.objects.for_scenario(scenario_id=self.scenario.id)
        handler_args = {"entry_points": [], "states": {}, "fallbacks": []}
        for step in steps:
            if Step.Template(step.template).is_command:
                command = step.handler_data.get(
                    "command", Step.Template(step.template).label
                )
                handler = CommandHandler(command, self.handle_step(step, bot_runner))
                if step.is_entry_point:
                    handler_args["entry_points"].append(handler)
            else:
                regex = step.handler_data.get("filter_regex")
                if regex:
                    step_filter = filters.Regex(regex)
                else:
                    step_filter = filters.TEXT & ~filters.COMMAND
                handler = MessageHandler(
                    step_filter, self.handle_step(step, bot_runner)
                )
                if step.is_entry_point:
                    handler_args["entry_points"].append(handler)

            if step.result_state:
                self.add_state(step.result_state)

            if step.is_fallback:
                handler_args["fallbacks"].append(handler)

            on_state = step.on_state
            if on_state:
                self.add_state(on_state)
                idx = self.states[on_state]
                if idx not in handler_args["states"]:
                    handler_args["states"][idx] = []
                handler_args["states"][idx].append(handler)

            conv_handler = ConversationHandler(**handler_args)
            return [conv_handler]

    def handle_step(self, step: Step, bot_runner):
        """
        Возвращает асинхронную функцию-обработчик для конкретного шага сценария.

        :param step: Шаг сценария
        :param bot_runner: runner бота (используется для доступа к истории и клиенту AI)
        :return: Асинхронная функция для исполнения сообщения
        """

        async def step_clear_history(
            update: Update, context: ContextTypes.DEFAULT_TYPE
        ):
            """Очищает историю общения с ботом (если шаг - очистка истории)"""

            bot_runner.history = []

        async def step_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Отправляет текст сообщения по сценарию и клавиатуру, если она задана."""
            args = {}
            if step.message:
                args["text"] = step.message
            keyboard = step.handler_data.get("keyboard")
            if keyboard:
                args["reply_markup"] = ReplyKeyboardMarkup(
                    keyboard, one_time_keyboard=True
                )
            await update.message.reply_text(**args)

        async def step_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Отправляет запрос к AI (если бот интегрируется c AI) и отвечает пользователю."""
            messages = []
            system = step.handler_data.get("system")
            if system:
                messages.append({"role": "system", "content": system})
            if bot_runner.history:
                messages.extend(bot_runner.history)
            text = update.message.text
            ai_context = step.handler_data.get("context")
            if ai_context:
                text = f"{text}\nДополнительный контекст: {ai_context}"
            question = {"role": "user", "content": text}
            messages.append(question)
            response = bot_runner.ai_client.chat.completions.create(
                model=bot_runner.ai_model, messages=messages
            )
            bot_runner.history.append(question)
            bot_runner.history.append(
                {
                    "role": "assistant",
                    "content": response.choices[0].message.content,
                }
            )
            await self.send_split_message(update, response.choices[0].message.content)

        actions = []
        if step.template == step.Template.CLEAR:
            actions.append(step_clear_history)
        if step.is_using_ai:
            actions.append(step_question)
        actions.append(step_message)

        async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Главная асинхронная функция реакции шага. Последовательно выполняет все действия шага."""
            try:
                for action in actions:
                    await action(update, context)
                if step.is_end:
                    return ConversationHandler.END
                return self.states.get(step.result_state)
            except Exception as e:
                logger.error(
                    f"Error handling command {action}, bot {bot_runner.bot_instance.name}: {e}"
                )
                await update.message.reply_text(f"Error: {str(e)}")

        return handle
