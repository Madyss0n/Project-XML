import codecs
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from app.validator import SCHEMAS, XMLValidationError, validate_xml

ROOT = Path(__file__).resolve().parent.parent


def normalize_encoding(text: str) -> str:
    return re.sub(r'(<\?xml\s+[^?]*encoding=)([\x22\x27])[^\x22\x27]+\2',
                  r'\1"UTF-8"', text, count=1)


def decode_xml(data: bytes) -> str:
    """Decode even malformed XML for editing; normalize the declaration to UTF-8."""
    if data.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        encoding = 'utf-32'
    elif data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        encoding = 'utf-16'
    elif data.startswith(b'\x00<\x00?'):
        encoding = 'utf-16-be'
    elif data.startswith(b'<\x00?\x00'):
        encoding = 'utf-16-le'
    else:
        declaration = re.match(br'<\?xml\s+[^?]*encoding=[\x22\x27]([^\x22\x27]+)', data)
        encoding = declaration.group(1).decode('ascii') if declaration else 'utf-8-sig'
    text = data.decode(encoding)
    return normalize_encoding(text).replace('\r\n', '\n').replace('\r', '\n')


class ValidatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('XML / XSD — проверка документов')
        self.geometry('1150x850')
        self.minsize(850, 600)
        self.path = None
        self.saved_text = ''
        self.schema = tk.StringVar(value='people')
        self.status = tk.StringVar(value='Откройте XML или вставьте документ в редактор.')
        bar = ttk.Frame(self, padding=8)
        bar.pack(fill='x')
        ttk.Button(bar, text='Открыть XML…', command=self.open_file).pack(side='left')
        ttk.Button(bar, text='Перечитать файл', command=self.reload).pack(side='left', padx=5)
        ttk.Button(bar, text='Сохранить как…', command=self.save_as).pack(side='left')
        ttk.Label(bar, text='   Схема: ').pack(side='left')
        combo = ttk.Combobox(bar, textvariable=self.schema, values=list(SCHEMAS), state='readonly', width=12)
        combo.pack(side='left')
        combo.bind('<<ComboboxSelected>>', lambda _: self.invalidate())
        ttk.Button(bar, text='Проверить (F5)', command=self.validate).pack(side='right')
        self.file_label = ttk.Label(self, text='Новый документ • сохранение в UTF-8', padding=(8, 0))
        self.file_label.pack(fill='x')
        panes = ttk.Panedwindow(self, orient='vertical')
        panes.pack(fill='both', expand=True, padx=8, pady=8)
        self.editor = ScrolledText(panes, wrap='none', undo=True, font=('Consolas', 11), height=22)
        panes.add(self.editor, weight=3)
        self.editor.tag_configure('error_line', background='#ffe0df')
        self.editor.bind('<<Modified>>', self.on_modified)
        results = ttk.Frame(panes)
        panes.add(results, weight=2)
        ttk.Label(results, text='Ошибки: выберите строку, чтобы увидеть подсказку и место в XML.').pack(anchor='w')
        error_list = ttk.Frame(results)
        error_list.pack(fill='both', expand=True)
        self.errors = ttk.Treeview(error_list, columns=('line', 'category', 'message'), show='headings', height=5)
        for col, label, width in [('line', 'Строка', 65), ('category', 'Категория', 110), ('message', 'Сообщение валидатора', 800)]:
            self.errors.heading(col, text=label)
            self.errors.column(col, width=width, stretch=col == 'message')
        scrollbar = ttk.Scrollbar(error_list, orient='vertical', command=self.errors.yview)
        self.errors.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.errors.pack(side='left', fill='both', expand=True)
        self.errors.bind('<<TreeviewSelect>>', self.select_error)
        self.details = ScrolledText(results, wrap='word', height=6, state='disabled', font=('Segoe UI', 10))
        self.details.pack(fill='both', expand=True, pady=(6, 0))
        ttk.Label(self, textvariable=self.status, padding=8, wraplength=1050).pack(fill='x')
        self.issues = []
        self.bind('<F5>', lambda _: self.validate())
        self.protocol('WM_DELETE_WINDOW', self.close)

    def text(self):
        return self.editor.get('1.0', 'end-1c')

    def set_details(self, text):
        self.details.configure(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', text)
        self.details.configure(state='disabled')

    def invalidate(self):
        self.errors.delete(*self.errors.get_children())
        self.issues = []
        self.editor.tag_remove('error_line', '1.0', 'end')
        self.set_details('')
        self.status.set('Документ или схема изменены. Нажмите «Проверить» для актуального результата.')

    def on_modified(self, _):
        if self.editor.edit_modified():
            self.invalidate()
            self.editor.edit_modified(False)

    def allow_discard(self):
        return self.text() == self.saved_text or messagebox.askyesno(
            'Несохранённые изменения', 'Продолжить без сохранения изменений?', parent=self)

    def load(self, path):
        try:
            content = decode_xml(path.read_bytes())
        except (OSError, UnicodeError, LookupError) as exc:
            messagebox.showerror('Не удалось открыть XML', str(exc), parent=self)
            return
        self.path = path
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', content)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.saved_text = content
        self.file_label.configure(text=f'{path} • сохранение в UTF-8')
        self.validate()

    def open_file(self):
        if not self.allow_discard():
            return
        path = filedialog.askopenfilename(parent=self, initialdir=ROOT / 'examples', filetypes=[('XML', '*.xml'), ('Все файлы', '*.*')])
        if path:
            self.load(Path(path))

    def reload(self):
        if self.path and self.allow_discard():
            self.load(self.path)

    def save_as(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.xml',
            initialfile=self.path.name if self.path else 'document.xml', filetypes=[('XML', '*.xml')])
        if not path:
            return
        try:
            content = normalize_encoding(self.text())
            Path(path).write_bytes(content.encode('utf-8'))
        except (OSError, UnicodeError) as exc:
            messagebox.showerror('Ошибка сохранения', str(exc), parent=self)
            return
        self.path = Path(path)
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', content)
        self.editor.edit_modified(False)
        self.saved_text = content
        self.file_label.configure(text=f'{path} • UTF-8')
        self.validate()

    def validate(self):
        self.invalidate()
        try:
            root = validate_xml(normalize_encoding(self.text()).encode('utf-8'), SCHEMAS[self.schema.get()])
        except XMLValidationError as exc:
            self.issues = exc.issues
            for i, issue in enumerate(self.issues):
                self.errors.insert('', 'end', iid=str(i), values=(issue.line, issue.category, issue.message))
            self.status.set(f'Проверка не пройдена. Ошибок: {len(self.issues)}. Исправьте XML и нажмите F5.')
            if self.issues:
                self.errors.selection_set('0')
                self.select_error()
        except (RuntimeError, UnicodeError) as exc:
            self.status.set('Проверка не выполнена.')
            self.set_details(str(exc))
        else:
            self.status.set(f'Валидация пройдена. Схема: {self.schema.get()}. Записей: {len(root)}. Проверен текст редактора.')
            self.set_details('XML синтаксически корректен и соответствует выбранной XSD-схеме. Изменения можно сохранить кнопкой «Сохранить как…».')

    def select_error(self, _=None):
        selection = self.errors.selection()
        if not selection:
            return
        issue = self.issues[int(selection[0])]
        self.set_details(f'{issue}\nПуть: {issue.path or "не определён"}')
        self.editor.tag_remove('error_line', '1.0', 'end')
        if issue.line > 0:
            self.editor.tag_add('error_line', f'{issue.line}.0', f'{issue.line}.end')
            self.editor.see(f'{issue.line}.0')

    def close(self):
        if self.allow_discard():
            self.destroy()


if __name__ == '__main__':
    ValidatorApp().mainloop()
