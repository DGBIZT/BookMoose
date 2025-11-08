Кастомная команда заполнения genres:
python manage.py import_genres data/genres.csv --user-id=1
Кастомная команда заполнения books
python manage.py fill_books data/books.xlsx --user-id 1
Обновление количества экземпляров книг:
POST http://127.0.0.1:8000/books/books/11/add_copies/ 
{
  "count": 2  // Создать 2 экземпляра
}

Получить экземпляры книг
GET http://127.0.0.1:8000/books/instances/
Получить экземпляр книги
GET http://127.0.0.1:8000/books/instances/id/

Выдача книги:
POST http://127.0.0.1:8000/loans/loans/
{
  "book_instance": 1, // ID экземпляра
  "user": 2          // ID пользователя, которому выдаём книгу
  "due_date": "2025-11-13T00:00:00Z",  // срок возврата (ISO 8601)
  "notes": "Книга выдана на 7 дней"

}

Вернуть книгу:
PATCH http://127.0.0.1:8000/loans/id/
{
  "is_returned": true
}
