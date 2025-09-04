from django.contrib import admin
from django import forms
from .models import Bot, Scenario, Step
from django.contrib.auth import get_user_model


User = get_user_model()


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "created_at",
        "current_scenario",
        "is_active",
        "is_running",
    ]
    date_hierarchy = "created_at"


class ScenarioAdminForm(forms.ModelForm):

    class Meta:
        model = Scenario
        fields = ["title", "scenario_type"]


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
    list_display = ["id", "title", "owner"]
    readonly_fields = ["id"]
    list_display_links = ["title"]
    fields = ["title", "owner", "default_state_title"]
    autocomplete_fields = ["owner"]
    inlines = [StepInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "step_set" in form.base_fields:
            form.base_fields["step_set"].widget.forward = ["scenario"]
        return form

    def save_model(self, request, obj, form, change):
        obj._default_state_title = (
            form.cleaned_data.get("default_state_title") or "Default state"
        )
        super().save_model(request, obj, form, change)


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "scenario"]
