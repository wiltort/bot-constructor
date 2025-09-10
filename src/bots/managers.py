from django.db import models


class BotManager(models.Manager):
    def get_active_bots(self, user=None):
        """Возвращает все активные боты, опционально для конкретного пользователя."""
        qs = self.filter(is_active=True)
        if user:
            qs = qs.filter(owner=user)
        return qs

    def get_running_bots(self, user=None):
        """Возвращает все запущенные боты, опционально для конкретного пользователя."""
        qs = self.filter(is_running=True)
        if user:
            qs = qs.filter(owner=user)
        return qs

    def get_stopped_bots(self, user=None):
        """Возвращает все активные и остановленные боты, опционально для конкретного пользователя."""
        qs = self.filter(is_active=True, is_running=False)
        if user:
            qs = qs.filter(owner=user)
        return qs

    def get_by_token(self, token, user=None):
        """Возвращает первого бота с указанным токеном, optionally owned by user. None если не найдено."""
        qs = self.filter(telegram_token=token)
        if user:
            qs = qs.filter(owner=user)
        return qs.first()

    def get_by_id(self, bot_id, user=None):
        """Возвращает первого бота по id, optionally owned by user. None если не найдено."""
        qs = self.filter(pk=bot_id)
        if user:
            qs = qs.filter(owner=user)
        return qs.first()

    def get_all_steps(self, bot_id, user=None):
        """
        Возвращает QuerySet шагов текущего сценария бота по id (и, опционально, user).
        Если бот или current_scenario не найден — вернет [].
        """
        qs = self.filter(pk=bot_id)
        if user:
            qs = qs.filter(owner=user)
        bot = qs.select_related("current_scenario").first()
        if bot and bot.current_scenario_id and hasattr(bot.current_scenario, "steps"):
            return bot.current_scenario.steps.all()
        from .models import Step

        return Step.objects.none()

    def get_all_active_steps(self, bot_id, user=None):
        """
        Возвращает QuerySet активных шагов текущего сценария бота.
        Если сценарий не назначен, возвращает пустой QuerySet.
        """
        qs = self.filter(pk=bot_id)
        if user:
            qs = qs.filter(owner=user)
        bot = qs.select_related("current_scenario").first()
        if bot and bot.current_scenario_id and hasattr(bot.current_scenario, "steps"):
            return bot.current_scenario.steps.filter(is_active=True)
        from .models import Step

        return Step.objects.none()

    def get_all_bots_with_steps(self):
        """
        Возвращает QuerySet всех ботов, с prefetch_related до связанных сценариев и шагов.
        """
        bots = self.select_related("current_scenario").prefetch_related(
            "current_scenario__steps"
        )
        return bots

    def get_steps_count(self, bot_id=None):
        from .models import Step, Bot

        if bot_id:
            qs = self.get_all_steps(bot_id)
            return qs.count()
        else:
            # Соберем все current_scenario для всех ботов
            scenario_ids = list(
                self.filter(current_scenario__isnull=False).values_list(
                    "current_scenario_id", flat=True
                )
            )
            # Посчитаем все шаги этих сценариев
            return Step.objects.filter(scenario_id__in=scenario_ids).count()


class StepManager(models.Manager):
    def for_scenario(self, scenario_id):
        return self.filter(scenario_id=scenario_id, is_active=True).order_by("priority")
