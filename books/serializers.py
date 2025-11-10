from rest_framework import serializers

from .models import Book, BookInstance


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

    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    author = serializers.SerializerMethodField()
    genre = serializers.StringRelatedField()
    created_by = serializers.StringRelatedField()
    cover_image_url = serializers.SerializerMethodField(read_only=True)

    available_copies = serializers.IntegerField(read_only=True)
    total_copies = serializers.IntegerField()

    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    def get_author(self, obj):
        return [str(author) for author in obj.author.all()]

    def get_cover_image_url(self, obj):
        if obj.cover_image:  # Проверяем, есть ли файл
            return obj.cover_image.url
        return None  # Если файла нет — возвращаем None

    def update(self, instance, validated_data):
        authors = validated_data.pop("author", None)
        if authors is not None:
            instance.author.set(authors)
        # Явно сохраняем total_copies, если передано
        if "total_copies" in validated_data:
            instance.total_copies = validated_data["total_copies"]
        return super().update(instance, validated_data)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "created_by",
            "created_by_email",
            "isbn",
            # 'publisher',
            "publication_year",
            "genre",
            "pages",
            "language",
            "description",
            "edition",
            # 'series',
            "available_copies",
            "total_copies",
            "cover_image",
            "cover_image_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
        ]  # created_by задаётся в perform_create (created_by Убрал из списка, т.к. падал тест)

        read_only_fields = [
            "created_at",
            "updated_at",
            "available_copies",
            "total_copies",
            "created_by",
            "created_by_email",
        ]
        extra_kwargs = {
            "isbn": {
                "required": False,
                "allow_blank": True,
            },
            "description": {
                "required": False,
                "allow_blank": True,
            },
            "edition": {
                "required": False,
                "allow_blank": True,
            },
            "cover_image": {
                "required": False,
            },
        }


class BookInstanceSerializer(serializers.ModelSerializer):
    class Meta:

        model = BookInstance
        fields = ["id", "copy_id", "status", "book", "borrower", "acquisition_date"]
        # read_only_fields = ['copy_id', 'book']  # copy_id генерируется автоматически, book задаётся при создании
