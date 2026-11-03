"""Веб-интерфейс Flask: форма загрузки и результат проверки XML."""
from flask import Flask, render_template, request

from app.database import parse_records
from app.logger import setup_logger
from app.validator import SCHEMAS, XMLValidationError, ValidationStorageError, validate_xml, decode_xml, normalize_encoding

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # До 2 МБ на запрос.
app.config['MAX_FORM_MEMORY_SIZE'] = app.config['MAX_CONTENT_LENGTH']
logger = setup_logger(__name__)

BOOK_COLUMNS = [('name', 'Название'), ('author', 'Автор'), ('publish_date', 'Дата публикации')]
PEOPLE_COLUMNS = [
    ('record_type', 'Тип'), ('person_id', 'ID'), ('full_name', 'ФИО'),
    ('birth_date', 'Дата рождения'), ('email1', 'Email 1'), ('email2', 'Email 2'),
    ('email3', 'Email 3'), ('phone', 'Телефон'), ('university', 'Вуз'),
    ('course', 'Курс'), ('organization', 'Организация'), ('position', 'Должность'),
]


def page(schema='people', filename=None, result=None, issues=None, records=None, warning=None, xml_text=None):
    """Один шаблон используется для формы, ошибок и успешного результата."""
    return render_template(
        'validate.html', schema=schema, filename=filename, result=result,
        issues=issues or [], records=records or [], warning=warning, xml_text=xml_text,
        columns=BOOK_COLUMNS if schema == 'books' else PEOPLE_COLUMNS,
    )


@app.route('/', methods=['GET', 'POST'])
def validate():
    if request.method == 'GET':
        return page()

    schema = request.form.get('schema', 'people')
    action = request.form.get('action', 'upload')
    xml_text = request.form.get('xml_text') if action == 'edit' else None
    filename = request.form.get('filename', 'document.xml') if action == 'edit' else None
    if schema not in SCHEMAS:
        return page(filename=filename, xml_text=xml_text,
                    result=('error', 'Неизвестная схема. Выберите People или Books.')), 400

    if action == 'upload':
        uploaded = request.files.get('xml_file')
        if uploaded is None or not uploaded.filename:
            return page(schema, result=('error', 'Выберите XML-файл для проверки.')), 400
        # Имя используется только для показа и истории, файл на диск не записываем.
        filename = uploaded.filename.replace('\\', '/').rsplit('/', 1)[-1]
        if not filename.lower().endswith('.xml'):
            return page(schema, filename, ('error', 'Нужен файл с расширением .xml.')), 400
        try:
            xml_text = decode_xml(uploaded.read())
        except (UnicodeError, LookupError):
            return page(schema, filename, ('error', 'Не удалось прочитать кодировку XML. Сохраните файл в UTF-8 и загрузите снова.')), 400
    elif action == 'edit' and xml_text is not None:
        filename = filename.replace('\\', '/').rsplit('/', 1)[-1] or 'document.xml'
        xml_text = normalize_encoding(xml_text).replace('\r\n', '\n').replace('\r', '\n')
    else:
        return page(schema, result=('error', 'Не передан текст XML для проверки.')), 400

    try:
        root = validate_xml(xml_text.encode('utf-8'), SCHEMAS[schema], source_name=filename)
    except XMLValidationError as exc:
        warning = 'Ошибки не удалось записать в БД. Подробности в журнале.' if exc.persistence_error else None
        return page(schema, filename, ('error', 'XML не прошёл валидацию.'),
                    issues=exc.issues, warning=warning, xml_text=xml_text), 422
    except ValidationStorageError as exc:
        records = parse_records(exc.root) if exc.root is not None else []
        return page(schema, filename, ('warning', 'XML корректен, но данные не записаны в БД.'),
                    records=records, warning='Повторите проверку позже. Подробности в журнале.', xml_text=xml_text), 503
    except (RuntimeError, OSError):
        logger.exception('Не удалось проверить файл %s по схеме %s', filename, schema)
        return page(schema, filename, ('error', 'Не удалось выполнить проверку. Подробности в журнале.'), xml_text=xml_text), 500

    records = parse_records(root)
    return page(schema, filename, ('success', 'Валидация пройдена. Данные сохранены в БД.'), records=records, xml_text=xml_text)


@app.errorhandler(413)
def upload_too_large(error):
    return page(result=('error', 'Превышен размер загрузки. Выберите XML меньше 2 МБ.')), 413
