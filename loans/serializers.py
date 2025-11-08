from rest_framework import serializers
from django.utils import timezone
from .models import BookLoan, BookInstance
from users.models import CustomUser



class BookLoanSerializer(serializers.ModelSerializer):
    """
    Сериализатор для выдач книг.

    Поля для чтения:
    - book_title: название книги (через book_instance.book.title)
    - copy_id: ID экземпляра (book_instance.copy_id)
    - user_username: логин пользователя
    - created_by_username: кто создал запись

    Поля для записи:
    - book_instance: ID экземпляра
    - user: ID пользователя
    - due_date: срок возврата
    - notes: примечания

    Автоматически:
    - loan_date: при создании
    - created_by: текущий пользователь (в ViewSet)
    - return_date: при установке is_returned=True
    """

    # Поля для удобного отображения
    book_title = serializers.CharField(
        source='book_instance.book.title',
        read_only=True
    )
    copy_id = serializers.CharField(
        source='book_instance.copy_id',
        read_only=True
    )
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )

    class Meta:
        model = BookLoan
        fields = [
            'id',
            'book_instance',
            'copy_id',
            'book_title',
            'user',
            'user_username',
            'loan_date',
            'return_date',
            'is_returned',
            'due_date',
            'notes',
            'created_by',
            'created_by_username',
        ]
        read_only_fields = [
            'loan_date',
            'return_date',
            'created_by',
        ]

    def validate(self, data):
        """
        Общая валидация:
        1. Проверка доступности экземпляра (если создаётся новая выдача).
        2. Контроль срока возврата.
        """
        book_instance = data.get('book_instance')
        due_date = data.get('due_date')

        # 1. Проверка при создании/обновлении
        if not self.instance:
            if not book_instance:
                raise serializers.ValidationError({
                    'book_instance': 'Обязательно укажите экземпляр книги.'
                })
            if book_instance.status != 'available':
                raise serializers.ValidationError({
                    'book_instance': 'Экземпляр уже выдан или недоступен.'
                })

        # 2. Проверка due_date
        if due_date:
            loan_date = self.instance.loan_date if self.instance else timezone.now()
            if due_date < loan_date:
                raise serializers.ValidationError({
                    'due_date': 'Срок возврата не может быть раньше даты выдачи.'
                })

        return data  # Убрали проверку loan_date/created_by — DRF уже обработал read_only

    def to_representation(self, instance):
        """
        Кастомизация вывода:
        - Скрываем copy_id и book_title, если экземпляр не указан.
        """
        rep = super().to_representation(instance)
        if not instance.book_instance:
            rep['copy_id'] = None
            rep['book_title'] = None
        return rep
