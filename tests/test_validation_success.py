import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import event, inspect, select
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.models import ValidationAccessRecord
from app.validator import SCHEMAS, XMLValidationError, ValidationStorageError, validate_file, validate_xml
from tests.support import isolate_history

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class SuccessfulValidationTests(unittest.TestCase):
    def setUp(self):
        self.engine, self.sessions = isolate_history(self)

    def rows(self):
        with self.sessions() as session:
            return session.scalars(select(ValidationAccessRecord).order_by(ValidationAccessRecord.id)).all()

    def test_people_fields_are_saved_in_columns(self):
        path = EXAMPLES / 'people_valid.xml'
        with self.assertLogs('app.validation_history', level='INFO') as logs:
            validate_file(path, SCHEMAS['people'])
        student, employee = self.rows()
        self.assertEqual((student.record_type, student.person_id, student.full_name),
                         ('student', 'student1', 'Иван Иванов'))
        self.assertEqual((student.birth_date, student.email1, student.email2, student.email3),
                         ('2003-05-21', 'ivan@example.org', 'ivan@university.example', None))
        self.assertEqual((student.phone, student.university, student.course),
                         ('+79991234567', 'НИЯУ МИФИ', 4))
        self.assertIsNone(student.organization)
        self.assertIsNone(student.name)
        self.assertEqual((employee.record_type, employee.organization, employee.position),
                         ('employee', 'Учебная лаборатория', 'Инженер'))
        self.assertEqual(employee.full_name, 'Анна Петрова')
        self.assertIsNone(employee.phone)
        self.assertIsNone(employee.university)
        self.assertEqual(student.validation_id, employee.validation_id)
        self.assertEqual(student.occurred_at, employee.occurred_at)
        self.assertEqual(student.source_name, str(path))
        self.assertEqual(student.schema_path, str(SCHEMAS['people'].resolve()))
        self.assertIn(student.validation_id, logs.output[0])

    def test_book_fields_are_saved(self):
        validate_file(EXAMPLES / 'books_valid.xml')
        book, = self.rows()
        self.assertEqual((book.record_type, book.name, book.author, book.publish_date),
                         ('book', 'Война и мир', 'Толстой', '1869-01-01'))
        self.assertIsNone(book.full_name)
        # Automatic history does not import into the old books table as a side effect.
        self.assertFalse(inspect(self.engine).has_table('books'))

    def test_repeated_checks_are_separate_attempts(self):
        for _ in range(2):
            validate_file(EXAMPLES / 'people_valid.xml', SCHEMAS['people'])
        rows = self.rows()
        self.assertEqual(len(rows), 4)
        self.assertNotEqual(rows[0].validation_id, rows[2].validation_id)

    def test_bad_xml_is_not_saved_as_success(self):
        with self.assertRaises(XMLValidationError):
            validate_file(EXAMPLES / 'people_invalid_email.xml', SCHEMAS['people'])
        self.assertFalse(inspect(self.engine).has_table('validation_acces'))

    def test_third_email_namespace_prefix_and_date_timezone(self):
        data = (EXAMPLES / 'people_valid.xml').read_bytes()
        data = data.replace(b'<phone>', b'<email>third@example.org</email><phone>', 1)
        data = data.replace(b'xmlns:p=', b'xmlns:person=')
        data = data.replace(b'p:StudentType', b'person:StudentType').replace(b'p:EmployeeType', b'person:EmployeeType')
        data = data.replace(b'2003-05-21', b'2003-05-21+05:00')
        validate_xml(data, SCHEMAS['people'], source_name='<редактор>')
        student = self.rows()[0]
        self.assertEqual(student.email3, 'third@example.org')
        self.assertEqual(student.birth_date, '2003-05-21+05:00')
        self.assertEqual(student.source_name, '<редактор>')

    def test_storage_failure_is_not_a_validation_error(self):
        failure = OperationalError('INSERT', {}, Exception('database is locked'))
        with patch('app.validation_history.SessionLocal', side_effect=failure):
            with self.assertLogs('app.validation_history', level='ERROR'):
                with self.assertRaises(ValidationStorageError) as caught:
                    validate_file(EXAMPLES / 'people_valid.xml', SCHEMAS['people'])
        self.assertIn('database is locked', str(caught.exception))
        self.assertFalse(inspect(self.engine).has_table('validation_errors'))

    def test_all_records_are_rolled_back_on_storage_failure(self):
        def reject_flush(session, context):
            raise SQLAlchemyError('storage failed after inserting both people')

        event.listen(self.sessions.class_, 'after_flush', reject_flush)
        self.addCleanup(event.remove, self.sessions.class_, 'after_flush', reject_flush)
        with self.assertLogs('app.validation_history', level='ERROR'):
            with self.assertRaises(ValidationStorageError):
                validate_file(EXAMPLES / 'people_valid.xml', SCHEMAS['people'])
        self.assertEqual(self.rows(), [])


if __name__ == '__main__':
    unittest.main()
