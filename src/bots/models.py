from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


# Create your models here.
class Bot(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    gpt_api_key = models.CharField(max_length=100)
    gpt_api_url = models.CharField(max_length=100)
    telegram_token = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)


class Scenario(models.Model):
    name = models.CharField(max_length=100)
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE,
                            related_name='scenarios')
    config = models.JSONField(default=dict)


class Step(models.Model):
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE,
                                 related_name='steps')
    order = models.IntegerField()
    prompt = models.TextField()  # Запрос к GPT
    response_handler = models.TextField(blank=True)  # Логика обработки ответа