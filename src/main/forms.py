from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from main.models import Category, Entry, Goal


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = [
            'kind', 'description', 'amount', 'category', 'occurred_on', 'note',
            'goal', 'goal_action',
        ]
        widgets = {
            'occurred_on': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0,00'}),
            'note': forms.TextInput(attrs={'placeholder': 'Opcional'}),
        }

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False
        if self.owner:
            self.fields['category'].queryset = Category.objects.filter(owner=self.owner)
            self.fields['goal'].queryset = Goal.objects.filter(owner=self.owner)
        self.fields['goal'].required = False
        self.fields['goal'].label = 'Meta relacionada (opcional)'
        self.fields['goal'].help_text = 'Escolha uma meta para guardar ou retirar este valor.'
        self.fields['goal_action'].required = False
        self.fields['goal_action'].label = 'O que fazer com a meta?'
        self.fields['goal_action'].help_text = 'Guardar registra uma despesa; retirar registra uma receita.'
        self.fields['goal_action'].choices = [('', 'Não movimentar meta')] + list(
            self.fields['goal_action'].choices[1:]
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        kind = cleaned_data.get('kind')
        goal = cleaned_data.get('goal')
        goal_action = cleaned_data.get('goal_action')
        if category and kind and category.kind != kind:
            self.add_error('category', 'Escolha uma categoria do mesmo tipo do lançamento.')
        if goal and not goal_action:
            self.add_error('goal_action', 'Escolha guardar ou retirar dinheiro da meta.')
        elif goal_action and not goal:
            self.add_error('goal', 'Selecione a meta que receberá esta movimentação.')
        elif goal and goal_action and kind:
            expected_kind = 'expense' if goal_action == 'deposit' else 'income'
            if kind != expected_kind:
                self.add_error(
                    'kind',
                    'Guardar na meta deve ser uma despesa; retirar da meta deve ser uma receita.',
                )
        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'kind']
        widgets = {'name': forms.TextInput(attrs={'placeholder': 'Ex.: Moradia'})}

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        kind = cleaned_data.get('kind')
        if self.owner and name and kind:
            duplicates = Category.objects.filter(owner=self.owner, name=name.strip(), kind=kind)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error('name', 'Você já tem uma categoria com esse nome e tipo.')
        return cleaned_data

    def save(self, commit=True):
        category = super().save(commit=False)
        if self.owner:
            category.owner = self.owner
        if commit:
            category.save()
        return category


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'current_amount', 'target_date', 'note']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ex.: Viagem, reserva de emergência'}),
            'target_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0,00'}),
            'current_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0,00'}),
            'target_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.TextInput(attrs={'placeholder': 'Opcional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['current_amount'].label = 'Valor já guardado (saldo inicial)'
        self.fields['current_amount'].help_text = 'Quanto você já guardou para esta meta.'
        self.fields['target_date'].required = False
        self.fields['note'].required = False
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label='E-mail', required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
