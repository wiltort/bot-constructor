from django.contrib import admin
from django import forms
from .models import Bot, Scenario, Step
from django.contrib.auth import get_user_model


User = get_user_model()


class BotAdminForm(forms.ModelForm):
    masked_gpt_api_key = forms.CharField(
        required=False,
        label='GPT API ключ',
        widget=forms.TextInput(attrs={'placeholder': 'Введите новый ключ'})
    )
    masked_telegram_token = forms.CharField(
        required=False,
        label='Телеграм токен',
        widget=forms.TextInput(attrs={'placeholder': 'Введите новый токен'})
    )

    class Meta:
        model = Bot
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.gpt_api_key:
            self.fields['masked_gpt_api_key'].initial = '•' * 20
        if self.instance and self.instance.telegram_token:
            self.fields['masked_telegram_token'].initial = '•' * 20
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        masked_gpt_api_key = self.cleaned_data.get('masked_gpt_api_key')
        masked_telegram_token = self.cleaned_data.get('masked_telegram_token')
        if masked_gpt_api_key and masked_gpt_api_key != '•' * 20:
            instance.gpt_api_key = masked_gpt_api_key
        if masked_telegram_token and masked_telegram_token != '•' * 20:
            instance.telegram_token = masked_telegram_token
        if commit:
            instance.save()
        return instance
        

@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    form = BotAdminForm
    fields = (
        "name",
        "description",
        "gpt_api_url",
        "ai_model",
        "masked_gpt_api_key",
        "masked_telegram_token",
        "created_at",
        "updated_at",
        "owner",
        "current_scenario",
        "is_active",
        "last_started",
        "last_stopped",
    )
    list_display = (
        "id",
        "name",
        "created_at",
        "current_scenario",
        "is_active",
        "is_running",
    )
    date_hierarchy = "created_at"
    readonly_fields = (
        "is_running",
        "created_at",
        "updated_at",
        "last_started",
        "last_stopped",
    )


class ScenarioAdminForm(forms.ModelForm):

    class Meta:
        model = Scenario
        fields = "__all__"


class StepForm(forms.ModelForm):
    class Meta:
        model = Step
        fields = "__all__"


class StepInline(admin.TabularInline):
    model = Step
    extra = 1
    form = StepForm


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    form = ScenarioAdminForm
    list_display = ("id", "title", "owner", "scenario_type")
    readonly_fields = ("id",)
    list_display_links = ("title",)
    fields = ("title", "owner", "scenario_type")
    autocomplete_fields = ("owner",)

@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "scenario", "on_state", "result_state", "is_entry_point", "template", "priority")
    list_filter = ("scenario", "on_state", "result_state")
    ordering = ("-is_entrypoint", "is_end", "priority", "on_state")

