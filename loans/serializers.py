from rest_framework import serializers
from .models import BookLoan
from users.models import CustomUser
from books.models import Book

class BookLoanSerializer(serializers.ModelSerializer):
    # Для удобства вывода имён (можно убрать, если не нужно)
    book_title = serializers.CharField(source='book.title', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    def validate(self, data):
        book = data.get('book')
        if book is not None:  # поле присутствует и не None
            if (BookLoan.objects
                    .filter(book=book, is_returned=False)
                    .exists()):
                raise serializers.ValidationError({
                    "book": "Книга уже выдана и не возвращена."
                })
        return data

    class Meta:
        model = BookLoan
        fields = [
            'id', 'book', 'book_title', 'user', 'user_username',
            'loan_date', 'return_date', 'is_returned',
            'due_date', 'notes', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['loan_date', 'created_by']
