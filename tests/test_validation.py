import tempfile
import unittest
from pathlib import Path

from app.gui import decode_xml, normalize_encoding
from app.validator import SCHEMAS, XMLValidationError, validate_file, validate_xml

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'


class ValidationTests(unittest.TestCase):
    def test_valid_examples(self):
        paths = list(EXAMPLES.glob('*_valid.xml'))
        self.assertEqual(len(paths), 2)
        for path in paths:
            with self.subTest(path=path.name):
                schema = SCHEMAS['books' if path.name.startswith('books') else 'people']
                self.assertIsNotNone(validate_file(path, schema))

    def test_invalid_examples_have_locations_and_hints(self):
        paths = list(EXAMPLES.glob('*_invalid_*.xml'))
        self.assertEqual(len(paths), 6)
        for path in paths:
            with self.subTest(path=path.name):
                schema = SCHEMAS['books' if path.name.startswith('books') else 'people']
                with self.assertRaises(XMLValidationError) as caught:
                    validate_file(path, schema)
                self.assertTrue(caught.exception.errors)
                for issue in caught.exception.issues:
                    self.assertGreater(issue.line, 0)
                    self.assertTrue(issue.suggestion)

    def test_fix_and_revalidate(self):
        data = (EXAMPLES / 'people_invalid_email.xml').read_bytes()
        with self.assertRaises(XMLValidationError):
            validate_xml(data, SCHEMAS['people'])
        fixed = data.replace(b'ivan-at-example.org', b'ivan@example.org')
        self.assertEqual(len(validate_xml(fixed, SCHEMAS['people'])), 2)

    def test_course_restriction(self):
        with self.assertRaises(XMLValidationError) as caught:
            validate_file(EXAMPLES / 'people_invalid_course.xml', SCHEMAS['people'])
        self.assertIn('maxInclusive', str(caught.exception))

    def test_syntax_errors_do_not_leak_between_calls(self):
        for data, expected in [(b'<a></b>', 'a'), (b'<x></y>', 'x')]:
            with self.assertRaises(XMLValidationError) as caught:
                validate_xml(data)
            self.assertEqual(len(caught.exception.issues), 1)
            self.assertIn(expected, caught.exception.issues[0].message)
            self.assertEqual(caught.exception.issues[0].category, 'Синтаксис XML')

    def test_default_book_schema_and_repository(self):
        from app.repository import parse_books_from_xml
        from app.models import Base, Book
        from app.repository import save_books
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session
        root = validate_file(EXAMPLES / 'books_valid.xml')
        books = parse_books_from_xml(root)
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            save_books(session, books)
            self.assertEqual(len(session.scalars(select(Book)).all()), 1)
        engine.dispose()

    def test_wrong_schema(self):
        with self.assertRaises(XMLValidationError):
            validate_file(EXAMPLES / 'people_valid.xml')

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            validate_file(EXAMPLES / 'does-not-exist.xml')

    def test_bad_schema_is_configuration_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'broken.xsd'
            path.write_text('<broken>', encoding='utf-8')
            with self.assertRaises(RuntimeError):
                validate_xml(b'<root/>', path)

    def test_doctype_and_external_entities_rejected(self):
        data = b'<!DOCTYPE Books [<!ENTITY secret SYSTEM "file:///not-to-be-read">]><Books xmlns="http://mephi3.ru">&secret;</Books>'
        with self.assertRaises(XMLValidationError) as caught:
            validate_xml(data)
        self.assertIn('DOCTYPE', str(caught.exception))

    def test_editor_encodings(self):
        for encoding in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'utf-32', 'windows-1251'):
            with self.subTest(encoding=encoding):
                text = '<?xml version="1.0" encoding="' + encoding + '"?><test>Привет</test>'
                decoded = decode_xml(text.encode(encoding))
                self.assertIn('Привет', decoded)
                self.assertIn('encoding="UTF-8"', decoded)
                self.assertEqual(normalize_encoding(decoded), decoded)


if __name__ == '__main__':
    unittest.main()
