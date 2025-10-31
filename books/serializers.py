from rest_framework import serializers
from .models import Book



class BookSerializer(serializers.ModelSerializer):
    # # Явно определяем читаемые поля для внешних связей
    # # Заглушки: поля примут ID, но не будут проверять существование объекта
    # author = serializers.PrimaryKeyRelatedField(
    #     queryset=None,  # Будет подключено позже
    #     allow_null=True,
    #     required=False,
    #     help_text="ID автора (модель Author)"
    # )
    # genre = serializers.PrimaryKeyRelatedField(
    #     queryset=None, # Будет подключено позже
    #     allow_null=True,
    #     required=False,
    #     help_text="ID жанра (модель Genre)"
    # )
    # publisher = serializers.PrimaryKeyRelatedField(
    #     queryset=None, # Будет подключено позже
    #     allow_null=True,
    #     required=False,
    #     help_text="ID издательства (модель Publisher)"
    # )
    # series = serializers.PrimaryKeyRelatedField(
    #     queryset=None, # Будет подключено позже
    #     allow_null=True,
    #     required=False,
    #     help_text="ID серии (модель Series)"
    # )

    created_by_email = serializers.EmailField(
        source='created_by.email',
        read_only=True,
        help_text="Email пользователя, добавившего книгу"
    )

    # Форматирование дат
    created_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
        help_text="Дата создания записи"
    )
    updated_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        read_only=True,
        help_text="Дата последнего обновления"
    )

    class Meta:
        model = Book
        fields = [
            'id',
            'title',
            'author',
            'author_name',
            'created_by',
            'created_by_email',
            'isbn',
            'publisher',
            'publisher_name',
            'publication_year',
            'genre',
            'genre_name',
            'pages',
            'language',
            'description',
            'edition',
            'series',
            'series_name',
            'available_copies',
            'total_copies',
            'cover_image',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']  # created_by задаётся в perform_create
        # extra_kwargs = { Как создам все приложения раскрыть комментарий
        #     'author': {'write_only': True},
        #     'publisher': {'write_only': True},
        #     'genre': {'write_only': True},
        #     'series': {'write_only': True},
        # }

    def validate(self, data):
        """
        Общая валидация на уровне объекта.
        1. Проверяем, что available_copies <= total_copies.
        2. Можно добавить другие бизнес‑правила.
        """
        available = data.get('available_copies')
        total = data.get('total_copies')

        if available is not None and total is not None:
            if available > total:
                raise serializers.ValidationError({
                    'available_copies': (
                        "Количество доступных копий не может превышать общее количество."
                    )
                })

        return data

    def to_representation(self, instance):
        """
        Кастомизация вывода данных.
        Здесь: оставляем всё как есть, но можно:
        - скрывать поля для определённых действий;
        - добавлять динамические поля.
        """
        rep = super().to_representation(instance)
        return rep

    def create(self, validated_data):
        """
        Можно добавить логику при создании (например, логирование).
        DRF автоматически сохранит, но здесь — точка для расширения.
        """
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Аналогично — точка для кастомной логики при обновлении.
        """
        return super().update(instance, validated_data)
