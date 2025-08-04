from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Scenario, Step

@receiver(post_save, sender=Scenario)
def create_default_state_for_scenario(sender, instance, created, **kwargs):
    if created:
        # step_message = getattr(instance, '_start_step_message', 'Привет!{username}')
        step_title = getattr(instance, '_start_step_title', 'start step')
        if not instance.steps.exists():
            Step.objects.create(
                scenario=instance,
                title=step_title,
                on_state='start',
                template=Step.Template.START,
            )