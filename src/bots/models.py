from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from encrypted_model_fields.fields import EncryptedCharField


User = get_user_model()


class Scenario(models.Model):
    """
    Представляет сценарий, являющися совокупностью состояний и шагов
    принадлежащий конкретному пользователю (owner). Каждый сценарий имеет
    уникальный заголовок для каждого пользователя и может иметь состояние
    по умолчанию (default_state)
    """
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name='пользователь',
        related_name='scenarios'
    )
    title = models.CharField(
        max_length=100,
        blank=False,
        verbose_name='название',
        )

    class Meta:
        ordering = ['title']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'title'],
                name='unique_scenario_per_owner'
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
        START = 'ST', 'start'
        CLEAR = 'CL', 'clear history'
        CUSTOM = 'CC', 'custom command'
        CHOICE = 'CH', 'choose button'
        CATHEGORY = 'CT', 'cathegory'
        OPERATOR = 'OP', 'call operator'
        QUESTION = 'QU', 'question'
        INPUT = 'IN', 'input data'

    title = models.CharField(
        max_length=100,
        verbose_name='название',
    )
    scenario = models.ForeignKey(
        Scenario, on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='сценарий'
    )
    on_state = models.CharField(verbose_name='Вызывающее состояние', )
    template = models.CharField(
        max_length=2,
        choices=Template,
        default=Template.CUSTOM,
        verbose_name='шаблон'
    )
    extra_context = models.JSONField(
        blank=True,
        null=True,
        verbose_name='дополнительный контекст',
    )

    class Meta:
        verbose_name = 'шаг'
        verbose_name_plural = 'шаги'
        constraints = [
            models.UniqueConstraint(
                fields=['scenario', 'title'],
                name='unique_step_per_scenario'
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
    name = models.CharField(max_length=200, verbose_name='имя')
    description = models.TextField(blank=True, null=True,
                                   verbose_name='описание')
    gpt_api_key = EncryptedCharField(
        max_length=200,
        verbose_name='API ключ',
        blank=True,
        null=True
    )
    gpt_api_url = models.CharField(
        max_length=200,
        verbose_name='API GPT URL',
        choices=settings.AVAILABLE_GPT_API_URLS,
        default=settings.AVAILABLE_GPT_API_URLS[0][0],
    )
    telegram_token = EncryptedCharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='телеграм токен'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='изменен')
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name='владелец'
    )
    current_scenario = models.ForeignKey(
        Scenario,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='текущий сценарий',
        related_name='bots'
    )
    is_active = models.BooleanField(blank=True, default=False, verbose_name='активен')

    class Meta:
        verbose_name = 'бот'
        verbose_name_plural = 'боты'
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'name'],
                name='unique_name_per_owner'
            )
        ]

    def clean(self):
        if self.is_active and (
            self.telegram_token is None or self.gpt_api_key is None or self.current_scenario is None
        ):
            raise ValidationError({
                'is_active': "Бот с отсутствующим телеграм токеном или "
                "API ключом невозможно активировать"
            })

    def __str__(self):
        return f"Bot: {self.name} (Owner: {self.owner})"
