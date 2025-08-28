from telegram.ext import Application
from src.bots.models import Bot


class BotInstance:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.app = Application.builder().token(bot.telegram_token).build()

    def setup_handlers(self):
        pass

    async def run(self):
        self.setup_handlers()
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(poll_interval=1)
