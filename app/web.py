from io import BytesIO
from sqlite3 import Error as SQLiteError

from flask import Flask, render_template, request, send_file

from app.database import parse_records, read_history
from app.logger import setup_logger
from app.validator import SCHEMAS, XMLValidationError, ValidationStorageError, validate_xml, decode_xml, normalize_encoding

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
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


@app.post('/download')
def download():
    filename = request.form.get('filename', '').replace('\\', '/').rsplit('/', 1)[-1]
    if not filename.lower().endswith('.xml') or any(ord(char) < 32 for char in filename):
        filename = 'document.xml'
    xml_text = normalize_encoding(request.form.get('xml_text', ''))
    return send_file(BytesIO(xml_text.encode('utf-8')), mimetype='application/xml',
                     as_attachment=True, download_name=filename)


@app.get('/history')
@app.get('/history/results', endpoint='history_results')
@app.get('/history/<uuid:validation_id>')
def history(validation_id=None):
    outcome = request.args.get('outcome', '')
    schema = request.args.get('schema', '')
    if outcome not in ('success', 'error'):
        outcome = ''
    if schema not in SCHEMAS:
        schema = ''
    filters = dict(outcome=outcome, schema=schema)
    show_table = request.endpoint == 'history_results' or request.args.get('show_table') == '1'
    if validation_id is None and not show_table:
        return render_template('history.html', **filters)
    try:
        rows = read_history(str(validation_id) if validation_id is not None else None, **filters)
    except SQLiteError:
        logger.exception('Не удалось прочитать историю проверок')
        return render_template('history.html', error='Не удалось прочитать историю проверок.'), 503

    for row in rows:
        row['schema_name'] = row['schema_path'].replace('\\', '/').rsplit('/', 1)[-1]

    if validation_id is None:
        return render_template('history.html', checks=rows, show_table=True, **filters)
    if not rows:
        return render_template('history.html', error='Проверка не найдена.'), 404
    check = rows[0]
    success = check['status'] == 'success'
    columns = BOOK_COLUMNS if check.get('record_type') == 'book' else PEOPLE_COLUMNS
    return render_template('history.html', check=check, columns=columns,
                           records=rows if success else [], issues=[] if success else rows, **filters)
