from abc import ABC, abstractmethod
from typing import Type
from telegram import Update
from telegram.ext import BaseHandler, ContextTypes
from src.bots.models import Step


class AbstractHandler(ABC):
    @abstractmethod
    async def callback_func(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    def get_handler(self, handler_class: Type[BaseHandler]):
        return handler_class()


class StartHandler(AbstractHandler):

    async def __call__(self, update, context):
        user = update.effective_user
        text = self.step.extra_context.get('message').format(username=user)
        await update.message.reply_text(text)


class HandlerFactory:
    def __init__(self, step: Step):
        self.step = step

    def get_handler(self):
        async def handler(update, context):
            user = update.effective_user
            message = self.step.extra_context.get('message').format(username=user)
            return message
