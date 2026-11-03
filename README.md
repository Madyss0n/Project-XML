# XML-валидатор с SQLite и логгером

Учебное приложение: открыть XML, проверить по XSD, увидеть ошибки и сохранить
результат в SQLite. Интерфейс пока на Tkinter; для будущего веб-интерфейса можно
использовать те же функции из `app/validator.py`.

## Запуск

В PyCharm выберите `.venv/Scripts/python.exe` и запустите `main.py`.
Для нового окружения:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Единственная внешняя зависимость - `lxml`. SQLite, логирование и Tkinter входят
в Python. Для окна нужен установленный Tcl/Tk.
Выберите схему `people` или `books`, откройте XML из `examples/`.
Проверка выполняется при открытии и по F5. Выбор ошибки подсвечивает строку и
показывает подсказку. «Сохранить как…» записывает исправленный XML в UTF-8.

## Файлы

```text
main.py                      запуск окна
app/
  gui.py                     интерфейс и XML-редактор
  validator.py               парсинг, XSD-проверка и подсказки
  database.py                таблицы SQLite и запись результатов
  logger.py                  настройка файла лога и консоли
  schemas/
    people.xsd               человек, студент и сотрудник с наследованием
    books.xsd                книги
examples/                    2 корректных и 6 некорректных XML
output/pdf/
  project_xml_overview.pdf    ранее подготовленный материал для курсовой
requirements.txt             только lxml
```

В PDF названия модулей на второй странице относятся к прежней структуре проекта.
Актуальный справочник файлов приведён выше.
`.venv`, настройки `.idea`, `books.db` и `log/app_log` - локальное окружение и данные.
Автотесты, ручные тестовые сценарии, дубли документации и временные файлы удалены.

## Как работает

1. `etree.fromstring()` строит дерево XML.
2. `etree.XMLSchema` проверяет его по выбранной XSD.
3. При успехе поля книги или человека записываются в `validation_acces`.
4. При ошибке диагностика записывается в `validation_errors` и лог.

DOCTYPE не поддерживается, внешние сущности не раскрываются.
Строки одного документа записываются одной транзакцией: либо все, либо ни одной.
Если SQLite недоступна, приложение отдельно сообщает о сбое записи.

Схема People содержит абстрактный `PersonType`: fullName, birthDate, contacts,
обязательный уникальный id. `StudentType` наследует его и добавляет university и
course (1-6). `EmployeeType` добавляет organization и position. В contacts допускаются
1-3 email и необязательный phone. Конкретный тип задаётся через `xsi:type`.

## База данных

`books.db` всегда находится в корне проекта, независимо от папки запуска.
Таблицы и индексы описаны обычным SQL в `app/database.py`. Создаются при первой
записи и проверяются один раз за запуск. Существующие записи БД сохраняются.

| Таблица | Содержание |
| --- | --- |
| `validation_acces` | Поля корректных книг, студентов и сотрудников |
| `validation_errors` | Ошибки XML и подсказки |
| `books` | Старые записи книг, если остались от прежней версии; новый код таблицу не использует |

Общие поля истории: `id`, `validation_id`, `occurred_at` (UTC), `source_name`,
`schema_path`. `validation_id` группирует строки одной попытки. Открытие файла
или F5 добавляет новую попытку. Между таблицами нет внешних ключей.

В `validation_acces` дополнительно хранятся:

- `record_type`: book, student или employee;
- книга: `name`, `author`, `publish_date`;
- человек: `person_id`, `full_name`, `birth_date`, `email1`, `email2`, `email3`, `phone`;
- студент: `university`, `course`;
- сотрудник: `organization`, `position`.

Одна книга или человек - одна строка. Неиспользуемые поля имеют значение NULL.
Даты хранятся как XML-текст. Исходный XML целиком не сохраняется.
В `validation_errors` дополнительно хранятся `category`, `line`, `column`,
`xpath`, `message`, `suggestion`. Значение 0 означает неизвестную позицию.

Для просмотра в DBeaver создайте подключение SQLite, укажите файл `books.db`,
откройте Tables → таблица → Data. Структура доступна на вкладке Diagram / ER Diagram.

```sql
SELECT * FROM validation_acces ORDER BY id DESC;
SELECT * FROM validation_errors ORDER BY id DESC;
SELECT name, sql FROM sqlite_master WHERE type = 'table';
```

## Логирование

`log/app_log` содержит время, уровень, имя модуля и сообщение. Записи также
выводятся в консоль: INFO для успеха, WARNING для ошибок XML, ERROR со стеком для
технических сбоев. Время в логе локальное, в SQLite - UTC.

## Вызов из Python

```python
from app.validator import validate_file, SCHEMAS, XMLValidationError, ValidationStorageError

try:
    root = validate_file('examples/people_valid.xml', SCHEMAS['people'])
    print('Сохранено записей:', len(root))
except XMLValidationError as error:
    print(*error.errors, sep='\n')
except ValidationStorageError as error:
    print(error)
```

`validate_xml(data, schema_path, source_name='document.xml')` проверяет байты.
Без схемы используется `books.xsd`. Ошибка чтения файла возвращается как OSError,
загрузки XSD - RuntimeError. Кнопка просмотра БД в GUI и веб-интерфейс пока в планах.
