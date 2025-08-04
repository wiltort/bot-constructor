from dal import autocomplete
from .models import State


class StateAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return State.objects.none()
        queryset = State.objects.all()
        scenario_id = self.forwarded.get('scenario') or self.request.GET.get('scenario')
        if scenario_id:
            queryset = queryset.filter(scenario_id=scenario_id)
        if self.q:
            queryset = queryset.filter(title__icontains=self.q)
        return queryset