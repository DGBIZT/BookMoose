from rest_framework import serializers

from .models import Author


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = [
            "id",
            "last_name",
            "first_name",
            "middle_name",
            "birth_date",
            "death_date",
            "biography",
            "photo_url",
        ]
        read_only_fields = ["id"]  # id не должен изменяться
