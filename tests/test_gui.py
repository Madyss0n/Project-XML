"""Desktop integration tests; require Tk and a graphical session."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.gui import ValidatorApp

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.app = ValidatorApp()
        self.app.withdraw()
        self.app.update()

    def tearDown(self):
        self.app.destroy()

    def test_open_fix_save_reload(self):
        with patch('app.gui.filedialog.askopenfilename', return_value=str(EXAMPLES / 'people_invalid_email.xml')):
            self.app.open_file()
        self.app.update()
        self.assertTrue(self.app.issues)
        self.assertIn('name@example.org', self.app.details.get('1.0', 'end'))
        self.assertTrue(self.app.editor.tag_ranges('error_line'))
        fixed = self.app.text().replace('ivan-at-example.org', 'ivan@example.org')
        self.app.editor.delete('1.0', 'end')
        self.app.editor.insert('1.0', fixed)
        self.app.update()
        self.assertFalse(self.app.errors.get_children())
        self.app.validate()
        self.assertIn('Валидация пройдена', self.app.status.get())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'исправленный.xml'
            with patch('app.gui.filedialog.asksaveasfilename', return_value=str(output)):
                self.app.save_as()
            self.app.update()
            self.assertEqual(output.read_text(encoding='utf-8'), fixed)
            output.write_text(fixed.replace('<course>4</course>', '<course>0</course>'), encoding='utf-8')
            self.app.reload()
            self.app.update()
            self.assertTrue(self.app.issues)

    def test_cancel_keeps_unsaved_work(self):
        self.app.editor.insert('1.0', '<unsaved/>')
        self.app.update()
        with patch('app.gui.messagebox.askyesno', return_value=False), patch('app.gui.filedialog.askopenfilename') as dialog:
            self.app.open_file()
            dialog.assert_not_called()
        self.assertEqual(self.app.text(), '<unsaved/>')

    def test_schema_selection_and_empty_document(self):
        self.app.validate()
        self.assertTrue(self.app.issues)
        self.app.schema.set('books')
        self.app.load(EXAMPLES / 'books_valid.xml')
        self.app.update()
        self.assertIn('Валидация пройдена', self.app.status.get())


if __name__ == '__main__':
    unittest.main()
