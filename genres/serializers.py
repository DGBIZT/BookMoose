from rest_framework import serializers
from .models import Genre

class GenreSerializer(serializers.ModelSerializer):
    # Дополнительные читаемые поля
    parent_name = serializers.CharField(
        source='parent.name',
        read_only=True,
        allow_null=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    full_path = serializers.CharField(
        read_only=True
    )
    has_subgenres = serializers.BooleanField(
        read_only=True
    )

    class Meta:
        model = Genre
        fields = [
            'id',
            'name',
            'description',
            'parent',
            'parent_name',
            'order',
            'is_active',
            'created_by',
            'created_by_username',
            'full_path',
            'has_subgenres',
        ]
        read_only_fields = ['created_by', 'full_path', 'has_subgenres']

    def to_representation(self, instance):
        """Добавляем full_path и has_subgenres в ответ."""
        data = super().to_representation(instance)
        data['full_path'] = instance.get_full_path()
        data['has_subgenres'] = instance.has_subgenres
        return data
