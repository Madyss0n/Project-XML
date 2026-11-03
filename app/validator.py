from dataclasses import dataclass
from pathlib import Path
from lxml import etree
from app.logger import setup_logger
from app.validation_history import record_validation_failure, record_validation_success

logger = setup_logger(__name__)

SCHEMA_PATH = Path(__file__).parent / 'schemas' / 'books.xsd'
SCHEMAS = {'books': SCHEMA_PATH, 'people': SCHEMA_PATH.with_name('people.xsd')}

@dataclass(frozen=True)
class ValidationIssue:
    category: str
    line: int
    column: int
    path: str
    message: str
    suggestion: str

    def __str__(self):
        return (f'{self.category}, строка {self.line}, столбец {self.column}: '
                f'{self.message}\nКак исправить: {self.suggestion}')

class XMLValidationError(Exception):
    def __init__(self, errors: list[str], issues: list[ValidationIssue] | None = None):
        self.errors = errors
        self.issues = issues or []
        self.persistence_error = None
        super().__init__('; '.join(errors))


class ValidationStorageError(RuntimeError):
    """The XML is valid, but saving its parsed data failed."""

def _parser():
    return etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)

def _suggestion(message, code):
    if 'email' in message and 'pattern' in message:
        return 'Укажите email вида name@example.org, без пробелов.'
    if 'pattern' in message:
        return 'Проверьте шаблон из сообщения: телефон — +79991234567, индекс — 6 цифр.'
    if 'enumeration' in message:
        return 'Выберите допустимое значение из списка в сообщении (регистр важен).'
    if 'Duplicate key' in message:
        return 'Задайте уникальный id человеку или уберите повторяющийся email у одного человека.'
    if 'No match found for key-sequence' in message:
        return 'Укажите в personRef id человека, существующего в этом документе.'
    if 'required but missing' in message:
        return 'Добавьте обязательный атрибут из сообщения в открывающий тег.'
    if 'Missing child element' in message or 'not expected' in message:
        return 'Добавьте ожидаемый элемент из сообщения и проверьте порядок полей в xs:sequence схемы.'
    if 'No matching global declaration' in message:
        return 'Проверьте схему, корневой элемент и xmlns: People — urn:mephi:people; Books — http://mephi3.ru.'
    if 'abstract' in message or 'xsi:type' in message:
        return 'Для person задайте xsi:type="p:StudentType" либо "p:EmployeeType", объявите xmlns:p="urn:mephi:people" и xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance".'
    if 'date' in message:
        return 'Укажите существующую дату в формате ГГГГ-ММ-ДД, например 2003-05-21.'
    if any(word in message for word in ('minInclusive', 'maxInclusive', 'minLength', 'maxLength')):
        return 'Измените значение с учётом границы из сообщения; обязательный текст не должен быть пустым.'
    if 'DATATYPE' in code:
        return 'Проверьте тип: целое число без текста, дробное с точкой, boolean — true/false или 1/0.'
    return 'Сопоставьте элемент, его тип и ограничения с выбранной XSD-схемой.'

def _raise(issues):
    raise XMLValidationError([str(issue) for issue in issues], issues)

def _validate_xml(xml_bytes: bytes, schema_path: Path) -> etree._Element:
    parser = _parser()
    try:
        root = etree.fromstring(xml_bytes, parser)
    except etree.XMLSyntaxError as exc:
        issues = [ValidationIssue('Синтаксис XML', e.line, e.column, e.path or '', e.message,
                    'Проверьте парность тегов, кавычки атрибутов и экранирование & как &amp;.')
                  for e in parser.error_log]
        if not issues:
            issues = [ValidationIssue('Синтаксис XML', 0, 0, '', str(exc), 'Проверьте содержимое и кодировку XML.')]
        _raise(issues)
    if root.getroottree().docinfo.doctype:
        _raise([ValidationIssue('Формат XML', 1, 0, '', 'DOCTYPE не поддерживается.',
                               'Удалите DOCTYPE и замените пользовательские сущности обычным текстом.')])
    path = Path(schema_path) if schema_path is not None else SCHEMA_PATH
    try:
        schema = etree.XMLSchema(etree.parse(str(path), _parser()))
    except (OSError, etree.XMLSyntaxError, etree.XMLSchemaParseError) as exc:
        raise RuntimeError(f'Не удалось загрузить XSD-схему {path}: {exc}') from exc
    if not schema.validate(root):
        _raise([ValidationIssue('XSD', e.line, e.column, e.path or '', e.message,
                               _suggestion(e.message, e.type_name)) for e in schema.error_log])
    return root

def validate_xml(xml_bytes: bytes, schema_path: str | Path | None = None,
                 *, source_name: str | Path | None = None) -> etree._Element:
    """Validate XML, then store either diagnostics or successfully parsed records."""
    schema_path = Path(schema_path or SCHEMA_PATH).resolve()
    source = str(source_name) if source_name is not None else "<bytes>"
    try:
        root = _validate_xml(xml_bytes, schema_path)
    except XMLValidationError as exc:
        exc.persistence_error = record_validation_failure(exc.issues, schema_path, source)
        raise
    except RuntimeError:
        logger.exception("Ошибка загрузки XSD | источник=%s | схема=%s", source, schema_path)
        raise
    logger.info("Валидация пройдена | источник=%s | схема=%s", source, schema_path)
    storage_error = record_validation_success(root, schema_path, source)
    if storage_error:
        raise ValidationStorageError(f'XML прошёл валидацию, но данные не записаны в БД: {storage_error}')
    return root


def validate_file(path: str | Path, schema_path: str | Path | None = None) -> etree._Element:
    path = Path(path).resolve()
    return validate_xml(path.read_bytes(), schema_path, source_name=path)
