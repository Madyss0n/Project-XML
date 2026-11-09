import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from app.logger import setup_logger

DATABASE_PATH = Path(__file__).resolve().parent.parent / 'books.db'
logger = setup_logger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS validation_errors (
    id INTEGER PRIMARY KEY,
    validation_id VARCHAR(36) NOT NULL,
    occurred_at DATETIME NOT NULL,
    source_name TEXT NOT NULL,
    schema_path TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    line INTEGER NOT NULL,
    "column" INTEGER NOT NULL,
    xpath TEXT NOT NULL,
    message TEXT NOT NULL,
    suggestion TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS validation_acces (
    id INTEGER PRIMARY KEY,
    validation_id VARCHAR(36) NOT NULL,
    occurred_at DATETIME NOT NULL,
    source_name TEXT NOT NULL,
    schema_path TEXT NOT NULL,
    record_type VARCHAR(30) NOT NULL,
    name TEXT,
    author TEXT,
    publish_date TEXT,
    person_id TEXT,
    full_name TEXT,
    birth_date TEXT,
    email1 TEXT,
    email2 TEXT,
    email3 TEXT,
    phone TEXT,
    university TEXT,
    course INTEGER,
    organization TEXT,
    position TEXT
);
CREATE INDEX IF NOT EXISTS ix_validation_errors_validation_id ON validation_errors(validation_id);
CREATE INDEX IF NOT EXISTS ix_validation_errors_occurred_at ON validation_errors(occurred_at);
CREATE INDEX IF NOT EXISTS ix_validation_acces_validation_id ON validation_acces(validation_id);
CREATE INDEX IF NOT EXISTS ix_validation_acces_occurred_at ON validation_acces(occurred_at);
"""


@lru_cache(maxsize=4)
def _init_db(path):
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(SCHEMA_SQL)


def _save(table, records):
    if table not in ('validation_errors', 'validation_acces'):
        raise ValueError('Неизвестная таблица истории проверки')
    _init_db(str(DATABASE_PATH))
    if not records:
        return
    columns = list(records[0])
    fields = ', '.join(f'"{column}"' for column in columns)
    placeholders = ', '.join('?' for _ in columns)
    sql = f'INSERT INTO {table} ({fields}) VALUES ({placeholders})'
    values = [tuple(record[column] for column in columns) for record in records]
    with closing(sqlite3.connect(DATABASE_PATH)) as connection:
        with connection:
            connection.executemany(sql, values)


HISTORY_TABLES = {'success': 'validation_acces', 'error': 'validation_errors'}


def read_history(validation_id=None, *, outcome='', schema=''):
    if not DATABASE_PATH.is_file():
        return []
    uri = DATABASE_PATH.resolve().as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        existing = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
        queries = []
        params = []
        for status, table in HISTORY_TABLES.items():
            if table not in existing:
                continue
            if validation_id is not None:
                rows = connection.execute(
                    f"SELECT *, ? AS status FROM {table} WHERE validation_id = ? ORDER BY id",
                    (status, validation_id),
                ).fetchall()
                if rows:
                    return [dict(row) for row in rows]
            else:
                if outcome and outcome != status:
                    continue
                where = ''
                if schema:
                    where = "WHERE ('/' || replace(schema_path, char(92), '/')) LIKE ? "
                    params.append(f'%/{schema}.xsd')
                queries.append(
                    f"SELECT validation_id, occurred_at, source_name, schema_path, "
                    f"'{status}' AS status, COUNT(*) AS item_count FROM {table} "
                    f"{where}GROUP BY validation_id, occurred_at, source_name, schema_path"
                )
        if not queries:
            return []
        sql = ' UNION ALL '.join(queries) + ' ORDER BY occurred_at DESC, validation_id DESC LIMIT 30'
        return [dict(row) for row in connection.execute(sql, params)]


def _attempt(schema_path, source_name):
    return dict(
        validation_id=str(uuid4()),
        occurred_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=' '),
        source_name=str(source_name),
        schema_path=str(schema_path),
    )


def record_validation_failure(issues, schema_path, source_name):
    attempt = _attempt(schema_path, source_name)
    records = []
    for issue in issues:
        logger.warning('Ошибка валидации | проверка=%s | источник=%s | схема=%s | %s',
                       attempt['validation_id'], source_name, schema_path, issue)
        records.append(dict(
            **attempt, category=issue.category, line=issue.line, column=issue.column,
            xpath=issue.path, message=issue.message, suggestion=issue.suggestion,
        ))
    try:
        _save('validation_errors', records)
    except (sqlite3.Error, OSError) as exc:
        logger.exception('Не удалось сохранить ошибки в SQLite')
        return str(exc)
    return None


def parse_records(root):
    if root.tag == '{http://mephi3.ru}Books':
        ns = {'b': 'http://mephi3.ru'}
        return [dict(
            record_type='book', name=book.findtext('b:name', namespaces=ns),
            author=book.findtext('b:author', namespaces=ns),
            publish_date=book.findtext('b:publishDate', namespaces=ns),
        ) for book in root.findall('b:book', ns)]

    if root.tag != '{urn:mephi:people}People':
        raise ValueError('Сохранение по столбцам поддерживается для Books и People.')
    ns = {'p': 'urn:mephi:people'}
    records = []
    for person in root.findall('p:person', ns):
        subtype = person.get('{http://www.w3.org/2001/XMLSchema-instance}type').split(':')[-1]
        emails = [email.text for email in person.findall('p:contacts/p:email', ns)]
        course = person.findtext('p:course', namespaces=ns)
        records.append(dict(
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
    return records


def record_validation_success(root, schema_path, source_name):
    attempt = _attempt(schema_path, source_name)
    try:
        records = [dict(**attempt, **values) for values in parse_records(root)]
        _save('validation_acces', records)
    except (sqlite3.Error, OSError, ValueError) as exc:
        logger.exception('Не удалось сохранить данные успешной проверки в SQLite')
        return str(exc)
    logger.info('В validation_acces сохранено строк: %s | проверка=%s | источник=%s',
                len(records), attempt['validation_id'], source_name)
    return None
