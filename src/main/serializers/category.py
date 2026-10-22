from rest_framework import serializers

from main.models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'kind', 'created_at']
        read_only_fields = ['id', 'created_at']
        validators = []

    def validate_name(self, value):
        value = value.strip()
        request = self.context.get('request')
        kind = self.initial_data.get('kind', getattr(self.instance, 'kind', None))
        if request and kind:
            existing = Category.objects.filter(owner=request.user, name=value, kind=kind)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError('Você já tem uma categoria com esse nome e tipo.')
        return value
