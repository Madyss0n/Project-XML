import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import event, inspect, select
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.models import ValidationErrorRecord
from app.validator import SCHEMAS, XMLValidationError, validate_file, validate_xml
from tests.support import isolate_history

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.engine, self.sessions = isolate_history(self)

    def rows(self):
        with self.sessions() as session:
            return session.scalars(select(ValidationErrorRecord).order_by(ValidationErrorRecord.id)).all()

    def fail(self, data, source_name=None):
        with self.assertRaises(XMLValidationError) as caught:
            validate_xml(data, SCHEMAS['people'], source_name=source_name)
        return caught.exception

    def test_schema_error_is_logged_and_saved_with_source(self):
        path = EXAMPLES / 'people_invalid_email.xml'
        self.assertFalse(inspect(self.engine).has_table('validation_errors'))
        with self.assertLogs('app.validation_history', level='WARNING') as logs:
            with self.assertRaises(XMLValidationError) as caught:
                validate_file(path, SCHEMAS['people'])
        row, = self.rows()
        issue, = caught.exception.issues
        self.assertEqual(row.source_name, str(path))
        self.assertEqual(row.schema_path, str(SCHEMAS['people'].resolve()))
        self.assertEqual((row.category, row.line, row.column, row.xpath, row.message, row.suggestion),
                         (issue.category, issue.line, issue.column, issue.path, issue.message, issue.suggestion))
        self.assertIsNotNone(row.occurred_at)
        self.assertIn(row.validation_id, logs.output[0])
        self.assertIn(issue.message, logs.output[0])
        self.assertIsNone(caught.exception.persistence_error)

    def test_syntax_error_and_doctype_are_saved(self):
        self.fail(b'<a></b>')
        self.fail(b'<!DOCTYPE People><People/>')
        self.assertEqual([r.category for r in self.rows()], ['Синтаксис XML', 'Формат XML'])
        self.assertEqual(self.rows()[0].source_name, '<bytes>')

    def test_multiple_errors_share_attempt_and_retries_get_new_id(self):
        data = (EXAMPLES / 'people_invalid_email.xml').read_bytes().replace(b'<course>4</course>', b'<course>9</course>')
        self.fail(data, '<редактор>')
        first = self.rows()
        self.assertEqual(len(first), 2)
        self.assertEqual(first[0].validation_id, first[1].validation_id)
        self.assertEqual(first[0].occurred_at, first[1].occurred_at)
        self.fail(data, '<редактор>')
        self.assertNotEqual(first[0].validation_id, self.rows()[2].validation_id)

    def test_success_and_schema_config_failure_are_not_xml_error_rows(self):
        validate_file(EXAMPLES / 'people_valid.xml', SCHEMAS['people'])
        with self.assertRaises(RuntimeError):
            validate_xml(b'<People/>', EXAMPLES / 'missing.xsd')
        self.assertFalse(inspect(self.engine).has_table('validation_errors'))

    def test_storage_failure_keeps_validation_error_and_log(self):
        failure = OperationalError('INSERT', {}, Exception('database is locked'))
        with patch('app.validation_history.SessionLocal', side_effect=failure):
            with self.assertLogs('app.validation_history', level='WARNING') as logs:
                error = self.fail(b'<a></b>')
        self.assertIn('database is locked', error.persistence_error)
        self.assertEqual(error.issues[0].category, 'Синтаксис XML')
        self.assertTrue(any('Ошибка валидации' in line for line in logs.output))
        self.assertTrue(any('Не удалось сохранить' in line for line in logs.output))

    def test_transaction_rolls_back_all_errors(self):
        # Simulate failure after INSERTs, while the transaction is still open.
        def reject_flush(session, context):
            raise SQLAlchemyError('storage failure after flush')

        event.listen(self.sessions.class_, 'after_flush', reject_flush)
        self.addCleanup(event.remove, self.sessions.class_, 'after_flush', reject_flush)
        error = self.fail((EXAMPLES / 'people_invalid_email.xml').read_bytes())
        self.assertIsNotNone(error.persistence_error)
        self.assertEqual(self.rows(), [])


if __name__ == '__main__':
    unittest.main()
