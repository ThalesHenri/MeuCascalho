from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from main.models import Category, Entry
from main.services.goal_allocation_service import (
    save_entry_with_goal_allocation,
)


class EntrySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    goal_name = serializers.CharField(source='goal.name', read_only=True, default=None)

    class Meta:
        model = Entry
        fields = [
            'id', 'kind', 'description', 'amount', 'category', 'category_name',
            'occurred_on', 'note', 'goal', 'goal_name', 'goal_action',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_description(self, value):
        return value.strip()

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('O valor precisa ser maior que zero.')
        return value

    def validate_category(self, category):
        if category is None:
            return category
        request = self.context.get('request')
        if request and category.owner_id != request.user.id:
            raise serializers.ValidationError('Esta categoria não pertence à sua conta.')
        kind = self.initial_data.get('kind', getattr(self.instance, 'kind', None))
        if kind and category.kind != kind:
            raise serializers.ValidationError('A categoria deve ser do mesmo tipo do lançamento.')
        return category

    def validate_goal(self, goal):
        if goal is None:
            return goal
        request = self.context.get('request')
        if request and goal.owner_id != request.user.id:
            raise serializers.ValidationError('Esta meta não pertence à sua conta.')
        return goal

    def validate(self, attrs):
        category = attrs.get('category', getattr(self.instance, 'category', None))
        kind = attrs.get('kind', getattr(self.instance, 'kind', None))
        goal = attrs.get('goal', getattr(self.instance, 'goal', None))
        goal_action = attrs.get('goal_action', getattr(self.instance, 'goal_action', ''))
        if category and kind and category.kind != kind:
            raise serializers.ValidationError({'category': 'A categoria deve ser do mesmo tipo do lançamento.'})
        if goal and not goal_action:
            raise serializers.ValidationError({'goal_action': 'Escolha guardar ou retirar dinheiro da meta.'})
        if goal_action and not goal:
            raise serializers.ValidationError({'goal': 'Selecione a meta relacionada à movimentação.'})
        if goal and goal_action and kind:
            expected_kind = Entry.Kind.EXPENSE if goal_action == Entry.GoalAction.DEPOSIT else Entry.Kind.INCOME
            if kind != expected_kind:
                raise serializers.ValidationError({
                    'kind': 'Aporte na meta deve ser uma despesa; retirada deve ser uma receita.'
                })
        return attrs

    def create(self, validated_data):
        entry = Entry(**validated_data)
        request = self.context.get('request')
        if request:
            entry.owner = request.user
        try:
            return save_entry_with_goal_allocation(entry)
        except DjangoValidationError as error:
            raise serializers.ValidationError(getattr(error, 'message_dict', error.messages)) from error

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        try:
            return save_entry_with_goal_allocation(instance)
        except DjangoValidationError as error:
            raise serializers.ValidationError(getattr(error, 'message_dict', error.messages)) from error
