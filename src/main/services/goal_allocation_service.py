from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from main.models import Entry, Goal


def _signed_allocation(entry):
    if not entry or not entry.goal_id or not entry.goal_action:
        return Decimal('0.00')
    if entry.goal_action == Entry.GoalAction.DEPOSIT:
        return entry.amount
    return -entry.amount


@transaction.atomic
def save_entry_with_goal_allocation(entry):
    """Persist an entry and apply its net deposit/withdrawal to the linked goal."""
    previous = None
    if entry.pk:
        previous = Entry.objects.select_for_update().get(pk=entry.pk)

    previous_goal_id = previous.goal_id if previous else None
    current_goal_id = entry.goal_id
    affected_ids = sorted({goal_id for goal_id in (previous_goal_id, current_goal_id) if goal_id})
    goals = {
        goal.pk: goal
        for goal in Goal.objects.select_for_update().filter(pk__in=affected_ids).order_by('pk')
    }

    balances = {goal_id: goal.current_amount for goal_id, goal in goals.items()}
    if previous_goal_id:
        balances[previous_goal_id] -= _signed_allocation(previous)
    if current_goal_id:
        balances[current_goal_id] += _signed_allocation(entry)

    for goal_id, balance in balances.items():
        if balance < 0:
            raise ValidationError({'amount': 'O valor da retirada é maior que o saldo disponível na meta.'})

    entry.save()
    for goal_id, balance in balances.items():
        Goal.objects.filter(pk=goal_id).update(current_amount=balance)

    return entry


@transaction.atomic
def delete_entry_with_goal_allocation(entry):
    """Delete an entry and reverse the associated allocation, if any."""
    previous = Entry.objects.select_for_update().get(pk=entry.pk)
    if previous.goal_id:
        goal = Goal.objects.select_for_update().get(pk=previous.goal_id)
        balance = goal.current_amount - _signed_allocation(previous)
        if balance < 0:
            raise ValidationError('Não foi possível excluir: o saldo da meta ficaria negativo.')
        Goal.objects.filter(pk=goal.pk).update(current_amount=balance)
    previous.delete()
