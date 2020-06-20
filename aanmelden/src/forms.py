from django import forms
from .models import Presence


class ManualRegistrationForm(forms):
    class Meta:
        model = Presence

class AuthorCreate(CreateView):
    model = Author
    fields = ['name']