from django.db import models


class BotManager(models.Manager):
    def get_running_bots(self, user=None):
        """Возвращает все активные и запущенные боты, опционально для конкретного пользователя."""
        qs = self.filter(is_active=True, is_running=True)
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
        bot = self.get_by_id(bot_id, user)
        if bot and bot.current_scenario:
            return bot.current_scenario.steps.all()
        return []

    def get_all_active_steps(self, bot_id, user=None):
        bot = self.get_by_id(bot_id, user)
        if bot and bot.current_scenario:
            return bot.current_scenario.steps.filter(is_active=True)
        return []


class StepManager(models.Manager):
    def for_scenario(self, scenario_id):
        return self.filter(scenario_id=scenario_id, is_active=True).order_by(
            "priority"
        )
