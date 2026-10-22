from rest_framework import serializers

from main.models import Goal


class GoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.IntegerField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Goal
        fields = [
            'id', 'name', 'target_amount', 'current_amount', 'target_date', 'note',
            'progress_percentage', 'is_completed', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        return value.strip()

    def validate_target_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('O valor desejado precisa ser maior que zero.')
        return value

    def validate_current_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('O valor guardado não pode ser negativo.')
        return value
