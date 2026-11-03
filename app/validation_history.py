"""Store validation errors and successfully parsed records in SQLite."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionLocal
from app.logger import setup_logger
from app.models import ValidationErrorRecord, ValidationAccessRecord

logger = setup_logger(__name__)


def record_validation_failure(issues, schema_path, source_name):
    """Return a storage error message, if any; never replace the XML diagnostic."""
    validation_id = str(uuid4())
    occurred_at = datetime.now(timezone.utc).replace(tzinfo=None)
    for issue in issues:
        logger.warning(
            "Ошибка валидации | проверка=%s | источник=%s | схема=%s | %s",
            validation_id, source_name, schema_path, issue,
        )
    try:
        with SessionLocal() as session:
            # Also supports direct validate_xml() calls before the GUI starts.
            ValidationErrorRecord.__table__.create(bind=session.get_bind(), checkfirst=True)
            session.add_all([
                ValidationErrorRecord(
                    validation_id=validation_id, occurred_at=occurred_at,
                    source_name=source_name, schema_path=str(schema_path),
                    category=issue.category, line=issue.line, column=issue.column,
                    xpath=issue.path, message=issue.message, suggestion=issue.suggestion,
                )
                for issue in issues
            ])
            session.commit()
    except (SQLAlchemyError, OSError) as exc:
        logger.exception("Не удалось сохранить ошибки проверки %s в SQLite", validation_id)
        return str(exc)
    return None


def parse_validated_records(root):
    """Map the two supported XML structures to simple database columns."""
    rows = []
    if root.tag == '{http://mephi3.ru}Books':
        ns = {'b': 'http://mephi3.ru'}
        for book in root.findall('b:book', ns):
            rows.append(dict(
                record_type='book',
                name=book.findtext('b:name', namespaces=ns),
                author=book.findtext('b:author', namespaces=ns),
                publish_date=book.findtext('b:publishDate', namespaces=ns),
            ))
    elif root.tag == '{urn:mephi:people}People':
        ns = {'p': 'urn:mephi:people'}
        for person in root.findall('p:person', ns):
            subtype = person.get('{http://www.w3.org/2001/XMLSchema-instance}type').split(':')[-1]
            emails = [email.text for email in person.findall('p:contacts/p:email', ns)]
            course = person.findtext('p:course', namespaces=ns)
            rows.append(dict(
                record_type='student' if subtype == 'StudentType' else 'employee',
                person_id=person.get('id'),
                full_name=person.findtext('p:fullName', namespaces=ns),
                birth_date=person.findtext('p:birthDate', namespaces=ns),
                email1=emails[0],
                email2=emails[1] if len(emails) > 1 else None,
                email3=emails[2] if len(emails) > 2 else None,
                phone=person.findtext('p:contacts/p:phone', namespaces=ns),
                university=person.findtext('p:university', namespaces=ns),
                course=int(course) if course is not None else None,
                organization=person.findtext('p:organization', namespaces=ns),
                position=person.findtext('p:position', namespaces=ns),
            ))
    else:
        raise ValueError('Сохранение по столбцам поддерживается для схем Books и People.')
    return rows


def record_validation_success(root, schema_path, source_name):
    """Save every record from one document in a single transaction."""
    validation_id = str(uuid4())
    occurred_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        values = parse_validated_records(root)
        with SessionLocal() as session:
            ValidationAccessRecord.__table__.create(bind=session.get_bind(), checkfirst=True)
            session.add_all([
                ValidationAccessRecord(
                    validation_id=validation_id, occurred_at=occurred_at,
                    source_name=source_name, schema_path=str(schema_path), **row,
                )
                for row in values
            ])
            session.commit()
    except (SQLAlchemyError, OSError, ValueError) as exc:
        logger.exception('Не удалось сохранить данные успешной проверки %s в SQLite', validation_id)
        return str(exc)
    logger.info('В validation_acces сохранено строк: %s | проверка=%s | источник=%s',
                len(values), validation_id, source_name)
    return None
