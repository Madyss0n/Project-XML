# Учебная XSD-схема People

В `app/schemas/people.xsd` общий тип `PersonType` описывает человека. Два типа
наследуют его через `xs:extension`: `StudentType` и `EmployeeType`. Это главный
пример наследования в курсовой. Схема написана на XSD 1.0 и проверяется `lxml`.

```text
People
└── person (1 или более записей)
    ├── @id                       уникальный идентификатор
    ├── @xsi:type                 p:StudentType или p:EmployeeType
    ├── fullName                  полное имя
    ├── birthDate                 дата рождения
    ├── contacts
    │   ├── email (1-3)          электронная почта
    │   └── phone (0-1)          необязательный телефон
    └── поля подкласса
        ├── StudentType: university, course (1-6)
        └── EmployeeType: organization, position
```

`PersonType` абстрактный: для каждого `<person>` обязателен конкретный тип в
атрибуте `xsi:type`. У обоих подклассов сначала идут общие поля, затем собственные.
`xs:sequence` требует именно такой порядок. `id` имеет тип `xs:ID`, поэтому не
может повторяться. `birthDate` проверяется как `xs:date`; `email` - по упрощённому
шаблону `name@domain.tld`. Поле `course` допускает целые числа от 1 до 6.
Полное имя, вуз и должность пока имеют тип `xs:string`: дополнительные бизнес-
ограничения для этой учебной схемы не вводятся.

Корневой элемент и вложенные теги находятся в пространстве имён
`urn:mephi:people`. Чтобы указать наследника, XML объявляет это пространство
под префиксом `p`, а также стандартный префикс `xsi`:

```xml
<People xmlns="urn:mephi:people" xmlns:p="urn:mephi:people"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <person id="student1" xsi:type="p:StudentType">
    <!-- общие поля, затем university и course -->
  </person>
</People>
```

Этот фрагмент показывает объявление типа; готовый валидный документ находится
в `examples/people_valid.xml`.

## Набор примеров

В папке `examples/` ровно **2 верных** и **6 неверных** XML-файлов:

| Файл | Схема | Результат |
| --- | --- | --- |
| `people_valid.xml` | people | Студент и сотрудник, валидация проходит |
| `books_valid.xml` | books | Книга, валидация проходит |
| `people_invalid_email.xml` | people | Неверный формат email |
| `people_invalid_course.xml` | people | Курс выше допустимого значения 6 |
| `people_invalid_missing_field.xml` | people | Отсутствует `university` |
| `people_invalid_subtype.xml` | people | Для абстрактного `PersonType` не указан `xsi:type` |
| `people_invalid_syntax.xml` | people | Ошибка закрывающего тега |
| `books_invalid_missing_author.xml` | books | У книги отсутствует обязательный автор |

Для демонстрации откройте `people_invalid_email.xml`, замените
`ivan-at-example.org` на `ivan@example.org` и нажмите F5. Так видно переход от
ошибки к успешной проверке без создания XML внутри Python-кода.
