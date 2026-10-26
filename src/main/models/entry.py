from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from main.models.category import Category
from main.models.goal import Goal


class Entry(models.Model):
    class Kind(models.TextChoices):
        INCOME = 'income', 'Receita'
        EXPENSE = 'expense', 'Despesa'

    class GoalAction(models.TextChoices):
        DEPOSIT = 'deposit', 'Guardar na meta'
        WITHDRAW = 'withdraw', 'Retirar da meta'

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='entries')
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='entries',
        null=True,
        blank=True,
        verbose_name='categoria',
    )
    goal = models.ForeignKey(
        Goal,
        on_delete=models.SET_NULL,
        related_name='entries',
        null=True,
        blank=True,
        verbose_name='meta relacionada',
    )
    goal_action = models.CharField(
        'movimentação na meta', max_length=10,
        choices=GoalAction.choices, blank=True,
    )
    kind = models.CharField('tipo', max_length=10, choices=Kind.choices)
    description = models.CharField('descrição', max_length=120)
    amount = models.DecimalField('valor', max_digits=12, decimal_places=2)
    occurred_on = models.DateField('data', db_index=True)
    note = models.CharField('observação', max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-occurred_on', '-created_at']
        constraints = [
            models.CheckConstraint(check=Q(amount__gt=0), name='entry_amount_must_be_positive'),
        ]
        indexes = [models.Index(fields=['owner', 'occurred_on'], name='entry_owner_date_idx')]
        verbose_name = 'lançamento'
        verbose_name_plural = 'lançamentos'

    def clean(self):
        super().clean()
        if self.category_id:
            if self.owner_id and self.category.owner_id != self.owner_id:
                raise ValidationError({'category': 'A categoria precisa pertencer a esta conta.'})
            if self.kind and self.category.kind != self.kind:
                raise ValidationError({'category': 'A categoria deve ser do mesmo tipo do lançamento.'})
        if self.goal_id:
            if self.owner_id and self.goal.owner_id != self.owner_id:
                raise ValidationError({'goal': 'A meta precisa pertencer a esta conta.'})
            if not self.goal_action:
                raise ValidationError({'goal_action': 'Escolha se deseja guardar ou retirar dinheiro da meta.'})
            expected_kind = (
                self.Kind.EXPENSE if self.goal_action == self.GoalAction.DEPOSIT
                else self.Kind.INCOME
            )
            if self.kind and self.kind != expected_kind:
                raise ValidationError({
                    'kind': 'Aporte na meta deve ser uma despesa; retirada deve ser uma receita.'
                })
        elif self.goal_action:
            raise ValidationError({'goal': 'Selecione a meta relacionada à movimentação.'})

    def __str__(self):
        return f'{self.description} — {self.amount}'
