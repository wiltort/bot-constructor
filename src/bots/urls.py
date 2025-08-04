from .autocomplete import StateAutocomplete
from django.urls import path

urlpatterns = [
    path(
        'state-autocomplete/',
        StateAutocomplete.as_view(),
        name='state-autocomplete',
    )
]
