from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario, Convite, Palpite


class RegistroForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('username', 'password1', 'password2')
        labels = {
            'username': 'Nome de usuário',
        }

    def __init__(self, convite, *args, **kwargs):
        self.convite = convite
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.convite_usado = self.convite
        if commit:
            user.save()
        return user


SETS_CHOICES = [(i, str(i)) for i in range(4)]

class PalpiteForm(forms.ModelForm):
    sets_a = forms.IntegerField(min_value=0, max_value=3, label='Sets Time A')
    sets_b = forms.IntegerField(min_value=0, max_value=3, label='Sets Time B')

    class Meta:
        model = Palpite
        fields = ('sets_a', 'sets_b')

    def clean(self):
        cleaned = super().clean()
        a = cleaned.get('sets_a')
        b = cleaned.get('sets_b')
        if a is not None and b is not None:
            if a == b:
                raise forms.ValidationError('Em vôlei não há empate. Um time deve ter 3 sets.')
            if max(a, b) != 3:
                raise forms.ValidationError('O vencedor deve ter exatamente 3 sets.')
        return cleaned
