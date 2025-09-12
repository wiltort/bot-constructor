from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.contrib import messages
from .models import Bot, Scenario, Step
from django.contrib.auth import get_user_model


User = get_user_model()


class BotAdminForm(forms.ModelForm):
    masked_gpt_api_key = forms.CharField(
        required=False,
        label="GPT API ключ",
        widget=forms.TextInput(attrs={"placeholder": "Введите новый ключ"}),
    )
    masked_telegram_token = forms.CharField(
        required=False,
        label="Телеграм токен",
        widget=forms.TextInput(attrs={"placeholder": "Введите новый токен"}),
    )

    class Meta:
        model = Bot
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.gpt_api_key:
            self.fields["masked_gpt_api_key"].initial = "•" * 20
        if self.instance and self.instance.telegram_token:
            self.fields["masked_telegram_token"].initial = "•" * 20

    def save(self, commit=True):
        instance = super().save(commit=False)
        masked_gpt_api_key = self.cleaned_data.get("masked_gpt_api_key")
        masked_telegram_token = self.cleaned_data.get("masked_telegram_token")
        if masked_gpt_api_key and masked_gpt_api_key != "•" * 20:
            instance.gpt_api_key = masked_gpt_api_key
        if masked_telegram_token and masked_telegram_token != "•" * 20:
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


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "scenario",
        "on_state",
        "result_state",
        "is_entry_point",
        "template",
        "priority",
    )
    list_filter = ("scenario", "on_state", "result_state")
    ordering = ("-is_entry_point", "is_end", "priority", "on_state")


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    form = ScenarioAdminForm
    list_display = ("id", "title", "owner", "scenario_type")
    readonly_fields = ("id", "steps_list", "add_step_button")
    list_display_links = ("title",)
    fields = ("title", "owner", "scenario_type", "steps_list", "add_step_button")
    autocomplete_fields = ("owner",)

    class Media:
        js = ("admin/scenario_admin.js",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/add-step/",
                self.admin_site.admin_view(self.add_step_view),
                name="scenario_add_step",
            ),
        ]
        return custom_urls + urls

    def steps_list(self, obj):
        if not obj.pk:
            return "Сохраните сценарий, чтобы добавить шаги"

        steps = obj.step_set.all().order_by(
            "-is_entry_point", "is_end", "priority", "on_state"
        )
        if not steps:
            return "Нет шагов"

        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f5f5f5;">'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">ID</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Название</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Состояние</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Результат</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Входная точка</th>'
        html += '<th style="padding: 8px; border: 1px solid #ddd;">Действия</th>'
        html += "</tr>"

        for step in steps:
            html += f"<tr>"
            html += f'<td style="padding: 8px; border: 1px solid #ddd;">{step.id}</td>'
            html += (
                f'<td style="padding: 8px; border: 1px solid #ddd;">{step.title}</td>'
            )
            html += f'<td style="padding: 8px; border: 1px solid #ddd;">{step.on_state}</td>'
            html += f'<td style="padding: 8px; border: 1px solid #ddd;">{step.result_state}</td>'
            html += f'<td style="padding: 8px; border: 1px solid #ddd;">{"✓" if step.is_entry_point else ""}</td>'
            html += f'<td style="padding: 8px; border: 1px solid #ddd;">'
            html += f'<a href="{reverse("admin:app_step_change", args=[step.id])}" target="_blank">Редактировать</a>'
            html += f"</td>"
            html += f"</tr>"

        html += "</table>"
        return format_html(html)

    steps_list.short_description = "Шаги сценария"

    def add_step_button(self, obj):
        if not obj.pk:
            return ""

        url = reverse("admin:scenario_add_step", args=[obj.id])
        return format_html(
            '<a href="{}" class="button" style="padding: 10px 15px; background-color: #417690; color: white; text-decoration: none; border-radius: 4px;" target="_blank">'
            "➕ Добавить новый шаг"
            "</a>",
            url,
        )

    add_step_button.short_description = "Добавить шаг"

    def add_step_view(self, request, object_id):
        scenario = get_object_or_404(Scenario, id=object_id)

        # Перенаправляем на стандартную форму добавления Step с предзаполненным scenario
        add_url = reverse("admin:bots_step_add")
        add_url += f"?scenario={scenario.id}"

        messages.info(
            request,
            f'Добавление шага для сценария "{scenario.title}". '
            f"После сохранения шага закройте это окно и обновите страницу сценария.",
        )

        return HttpResponseRedirect(add_url)
