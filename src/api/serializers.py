from rest_framework import serializers
from bots.models import Bot, Scenario, Step
import re


class BotControlSerializer(serializers.Serializer):
    """Сериализатор для массового управления ботами"""

    bot_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, max_length=100
    )


class BotStatusSerializer(serializers.ModelSerializer):
    """Сериализатор статуса бота"""

    steps_count = serializers.SerializerMethodField()

    class Meta:
        model = Bot
        fields = [
            "id",
            "name",
            "is_active",
            "is_running",
            "last_started",
            "last_stopped",
            "created_at",
            "updated_at",
            "steps_count",
        ]

    def get_steps_count(self, obj):
        if not obj.current_scenario__id:
            return 0
        return obj.objects.get_all_active_steps(obj.current_scenario__id).count()


class BotSerializer(serializers.ModelSerializer):
    """Сериализатор для Bot"""

    current_scenario = serializers.PrimaryKeyRelatedField(
        queryset=Scenario.objects.all()
    )
    status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bot
        fields = [
            "id",
            "name",
            "description",
            "gpt_api_key",
            "ai_model",
            "telegram_token",
            "current_scenario",
            "is_active",
            "is_running",
            "last_started",
            "last_stopped",
            "created_at",
            "updated_at",
            "status",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "telegram_token": {"write_only": True},
            "gpt_api_key": {"write_only": True},
            "is_running": {"read_only": True},
            "last_started": {"read_only": True},
            "last_stopped": {"read_only": True},
        }

    def get_status(self, obj):
        return "running" if obj.is_running else "stopped"

    def validate_telegram_token(self, value):
        """Валидация токена"""
        if value and ":" not in value:
            raise serializers.ValidationError(
                "Некорректный токен Telegram. Ожидается формат <id>:<hash>"
            )
        return value


class StepSerializer(serializers.ModelSerializer):
    """Сериализатор для Step"""

    class Meta:
        model = Step
        fields = [
            "id",
            "title",
            "is_active",
            "is_using_ai",
            "is_entry_point",
            "is_fallback",
            "is_end",
            "on_state",
            "result_state",
            "template",
            "priority",
            "message",
            "handler_data",
        ]


class ScenarioSerializer(serializers.ModelSerializer):
    """Сериализатор для Scenario"""

    bots = BotSerializer(many=True, read_only=True)
    steps = StepSerializer(many=True, read_only=True)

    class Meta:
        model = Scenario
        fields = ["id", "title", "scenario_type", "bots", "steps"]


class BotStepSerializer(serializers.ModelSerializer):
    """Сериализатор для BotHandler"""

    scenario = serializers.PrimaryKeyRelatedField(queryset=Scenario.objects.all())
    scenario_title = serializers.CharField(source="scenario.title", read_only=True)

    class Meta:
        model = Step
        fields = [
            "id",
            "title",
            "scenario",  # FK id сценария (можно исключить, если не нужно)
            "scenario_title",
            "is_active",
            "is_using_ai",
            "is_entry_point",
            "is_fallback",
            "is_end",
            "on_state",
            "result_state",
            "template",
            "priority",
            "message",
            "handler_data",
        ]
        read_only_fields = ("scenario_title", "bot_names")

    def get_bots_names(self, obj: Step):
        if not obj.scenario_id:
            return []
        return list(obj.scenario.bots.values_list("name", flat=True))

    def validate_handler_data(self, value):
        filter_exp = value.get("filter_regex")
        if filter_exp:
            try:
                pattern = re.compile(filter_exp)
                return value
            except re.error as e:
                raise serializers.ValidationError(
                    "Неверный формат выражения filter_regex"
                )
        keyboard = value.get("keyboard")
        if keyboard:
            if not isinstance(keyboard, list):
                raise serializers.ValidationError("Неверный формат клавиатуры")
            for row in keyboard:
                if not isinstance(row, list):
                    raise serializers.ValidationError("Неверный формат клавиатуры")
                for button in row:
                    if not isinstance(button, str):
                        raise serializers.ValidationError("Неверный формат клавиатуры")
