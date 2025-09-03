from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from encrypted_model_fields.fields import EncryptedCharField
from .managers import BotManager, StepManager


User = get_user_model()


class Scenario(models.Model):
    """
    Представляет сценарий, являющися совокупностью состояний и шагов
    принадлежащий конкретному пользователю (owner). Каждый сценарий имеет
    уникальный заголовок для каждого пользователя и может иметь состояние
    по умолчанию (default_state)
    """

    class ScenarioType(models.TextChoices):
        CONVERSATION = "CS", "Conversation"

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name="пользователь",
        related_name="scenarios",
    )
    title = models.CharField(
        max_length=100,
        blank=False,
        verbose_name="название",
    )
    scenario_type = models.CharField(
        max_length=2,
        choices=ScenarioType,
        default=ScenarioType.CONVERSATION,
        verbose_name="Тип сценария",
    )

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "title"], name="unique_scenario_per_owner"
            )
        ]
        verbose_name = "сценарий"
        verbose_name_plural = "сценарии"

    def __str__(self):
        return f"Scenario: {self.title} (Owner: {self.owner})"


class Step(models.Model):
    """
    Представляет шаг в сценарии, опционально связан с состоянием.
    Шаг определяет действия и переходы в сценарии.
    """

    class Template(models.TextChoices):
        START = "ST", "start"  # команда старт
        CLEAR = "CL", "clear"  # очистка истории
        HELP = "HL", "help"  # вызов справки
        STOP = "SP", "stop"  # стоп
        CUSTOM = "CC", "custom command"
        # CHOICE = 'CH', 'choose button'
        # CATHEGORY = 'CT', 'cathegory'
        # OPERATOR = 'OP', 'call operator'
        QUESTION = "QU", "question"  # Вопрос
        # INPUT = 'IN', 'input data'

        @property
        def is_command(self):
            return self in {
                type(self).START,
                type(self).CLEAR,
                type(self).HELP,
                type(self).STOP,
                type(self).CUSTOM
            }

    title = models.CharField(
        max_length=100,
        verbose_name="название",
    )
    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="сценарий",
    )
    is_active = models.BooleanField(verbose_name="Активен", default=True)
    is_using_ai = models.BooleanField(
        verbose_name="Использование запроса к AI", default=False
    )
    is_entry_point = models.BooleanField(verbose_name='Точка входа', default=False)
    is_fallback = models.BooleanField(verbose_name="шаг по умолчанию", default=False)
    is_end = models.BooleanField(verbose_name="Конец разговора", default=False)
    on_state = models.CharField(verbose_name="Вызывающее состояние", blank=True, default="")
    result_state = models.CharField(verbose_name="Выходное сотояние", blank=True, default="")
    template = models.CharField(
        max_length=2,
        verbose_name="Шаблон",
        choices=Template,
        default=Template.QUESTION
    )
    priority = models.PositiveSmallIntegerField(verbose_name="Приоритет", default=1)
    message = models.TextField(verbose_name="Текст сообщения", null=True, blank=True)
    handler_data = models.JSONField(verbose_name="Настройки для хендлеров", default=dict)
    # тип - словарь с полями:
    # keyboard: list[list[str]] - список кнопок в клавиатуре
    # system: str - Системный промпт
    # context: str - дополнительные данные для анализа
    # filter_regex: str - фильтр
    # command: str

    objects = StepManager()

    class Meta:
        verbose_name = "шаг"
        verbose_name_plural = "шаги"
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "title"], name="unique_step_per_scenario"
            )
        ]

    def __str__(self):
        return f"Step: {self.title} (Scenario: {self.scenario.title})"


class Bot(models.Model):
    """
    Представляет экземпляр бота, который имеет возможность настройки ключей
    API, токенов и ссылки на сценарий. Каждый бот принадлежит определенному
    пользователю (owner)
    """

    name = models.CharField(max_length=200, verbose_name="имя")
    description = models.TextField(blank=True, null=True, verbose_name="описание")
    gpt_api_key = EncryptedCharField(
        max_length=200, verbose_name="API ключ", blank=True, null=True
    )
    gpt_api_url = models.CharField(
        max_length=200,
        verbose_name="API GPT URL",
        choices=settings.AVAILABLE_GPT_API_URLS,
        default=settings.AVAILABLE_GPT_API_URLS[0][0],
    )
    ai_model = models.CharField(
        max_length=200,
        verbose_name="ai модель",
    )
    telegram_token = EncryptedCharField(
        max_length=200, blank=True, null=True, verbose_name="телеграм токен"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="изменен")
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="владелец",
        related_name="bots"
    )
    current_scenario = models.ForeignKey(
        Scenario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="текущий сценарий",
        related_name="bots",
    )
    is_active = models.BooleanField(blank=True, default=False, verbose_name="активен")
    is_running = models.BooleanField(default=True, verbose_name="запущен")
    objects = BotManager()
    last_started = models.DateTimeField(null=True, blank=True, verbose_name='время запуска')
    last_stopped = models.DateTimeField(null=True, blank=True, verbose_name='время остановки')

    class Meta:
        verbose_name = "бот"
        verbose_name_plural = "боты"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"], name="unique_name_per_owner"
            )
        ]

    def clean(self):
        if self.is_active and (
            self.telegram_token is None
            or self.gpt_api_key is None
            or self.current_scenario is None
        ):
            raise ValidationError(
                {
                    "is_active": "Бот с отсутствующим телеграм токеном или "
                    "API ключом невозможно активировать"
                }
            )

    def __str__(self):
        return f"Bot: {self.name} (Owner: {self.owner})"
