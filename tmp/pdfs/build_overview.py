from pathlib import Path
from math import atan2, cos, sin, pi
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf/project_xml_overview.pdf'
pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialBold', 'C:/Windows/Fonts/arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Consolas', 'C:/Windows/Fonts/consola.ttf'))
W,H = A4
c = canvas.Canvas(str(OUT), pagesize=A4)
c.setTitle('Project-XML: блок-схема, файлы, XSD и примеры валидации')
c.setAuthor('Project-XML')
ink=HexColor('#192E40'); blue=HexColor('#245C80'); line=HexColor('#516777')
light=HexColor('#EFF5F8'); red=HexColor('#984539'); green=HexColor('#316B55')

def text(x,y,s,size=10,font='Arial',color=ink):
    c.setFillColor(color); c.setFont(font,size); c.drawString(x,H-y,s)

def center(x,y,s,size=10,font='Arial',color=ink):
    c.setFillColor(color); c.setFont(font,size); c.drawCentredString(x,H-y,s)

def header(n,title,subtitle):
    text(36,35,'PROJECT-XML  /  КУРСОВАЯ РАБОТА',9,'ArialBold',blue)
    text(36,66,title,21,'ArialBold')
    text(36,86,subtitle,10,color=line)
    c.setStrokeColor(HexColor('#CBD7DF')); c.line(36,40,W-36,40)
    text(36,H-25,'XML / XSD • Python • lxml • Tkinter • SQLite',8,color=line)
    text(W-65,H-25,f'{n} / 4',9,color=line)

def block(x,y,w,h,label,kind='rect',fill=light,color=blue,size=10):
    c.setStrokeColor(color); c.setFillColor(fill); c.setLineWidth(1)
    if kind=='round': c.roundRect(x,H-y-h,w,h,13,stroke=1,fill=1)
    elif kind=='diamond':
        p=c.beginPath(); p.moveTo(x+w/2,H-y); p.lineTo(x+w,H-y-h/2); p.lineTo(x+w/2,H-y-h); p.lineTo(x,H-y-h/2); p.close(); c.drawPath(p,stroke=1,fill=1)
    elif kind=='input':
        p=c.beginPath(); p.moveTo(x+12,H-y); p.lineTo(x+w,H-y); p.lineTo(x+w-12,H-y-h); p.lineTo(x,H-y-h); p.close(); c.drawPath(p,stroke=1,fill=1)
    else: c.roundRect(x,H-y-h,w,h,3,stroke=1,fill=1)
    labels=label.split('\n'); yy=y+h/2-(len(labels)-1)*6+3.5
    for s in labels: center(x+w/2,yy,s,size,color=ink); yy+=12

def arrow(points,color=line):
    c.setStrokeColor(color); c.setFillColor(color); c.setLineWidth(1)
    p=c.beginPath(); p.moveTo(points[0][0],H-points[0][1])
    for x,y in points[1:]: p.lineTo(x,H-y)
    c.drawPath(p)
    x,y=points[-1]; a=atan2(y-points[-2][1],x-points[-2][0]); p=c.beginPath(); p.moveTo(x,H-y)
    for v in (a+pi-.45,a+pi+.45): p.lineTo(x+6*cos(v),H-(y+6*sin(v)))
    p.close(); c.drawPath(p,stroke=0,fill=1)

header(1,'Блок-схема работы приложения','Основной сценарий оконного валидатора: открыть, проверить, исправить.')
block(175,106,140,28,'Запуск main.py','round')
block(135,153,220,46,'Выбор XSD: people / books\nОткрытие XML-файла','input')
block(135,218,220,44,'Чтение и декодирование XML\nПоказ текста в редакторе')
block(135,283,220,68,'Парсинг XML\nуспешен?','diamond')
block(135,377,220,44,'Загрузка выбранной XSD\nПроверка структуры и значений')
block(135,442,220,68,'XML соответствует\nXSD-схеме?','diamond')
block(135,539,220,42,'Сообщение:\n«Валидация пройдена»',fill=HexColor('#EFF7F2'),color=green)
block(135,606,220,42,'«Сохранить как…»\nЗапись XML в UTF-8','input')
block(175,671,140,28,'Конец сценария','round')
for a,b in [(134,153),(199,218),(262,283),(351,377),(421,442),(510,539),(581,606),(648,671)]: arrow([(245,a),(245,b)])
text(254,367,'Да',9,color=green); text(254,530,'Да',9,color=green)
block(408,389,151,70,'Список ошибок\nСтрока и XPath\nПодсказка исправления',fill=HexColor('#FFF3EF'),color=red,size=9.5)
block(408,519,151,54,'Исправление XML\nв редакторе\nПовторная проверка: F5',fill=HexColor('#FFF3EF'),color=red,size=9.5)
arrow([(355,317),(483.5,317),(483.5,389)],red); text(366,309,'Нет',9,color=red)
arrow([(355,476),(385,476),(385,424),(408,424)],red); text(360,491,'Нет',9,color=red)
arrow([(483.5,459),(483.5,519)],red)
arrow([(483.5,573),(483.5,591),(386,591),(386,718),(68,718),(68,317),(135,317)],blue)
text(78,709,'Повторный парсинг текущего текста',9,color=blue)
# Compact notes accurately separate the existing database pipeline from the GUI.
style=ParagraphStyle('note',fontName='Arial',fontSize=8.7,leading=11,textColor=ink)
notes=[
'При открытии проверка запускается автоматически; после правок - по F5. Ошибки чтения файла или XSD показываются отдельно. DOCTYPE отклоняется.',
'Сохранение доступно и до успешной проверки. Схема выше показывает рекомендуемый цикл исправления документа.',
'SQLite: отдельный сценарий test_full.py → валидация книг → объекты Book → books.db. Оконный валидатор не записывает людей в БД.'
]
y=734
for s in notes:
    p=Paragraph(s,style); _,h=p.wrap(W-72,50); p.drawOn(c,36,H-y-h); y+=h+4
c.showPage()

header(2,'Назначение файлов проекта','Краткий справочник исходного кода, схем, примеров и проверок.')
body=ParagraphStyle('body',fontName='Arial',fontSize=9.1,leading=11.4,textColor=ink)
name=ParagraphStyle('name',parent=body,fontName='ArialBold',fontSize=9)

def section(y,title,rows):
    text(36,y,title,11,'ArialBold',blue)
    data=[[Paragraph(a,name),Paragraph(b,body)] for a,b in rows]
    t=Table(data,colWidths=[192,W-72-192])
    t.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[light,white]),
        ('LINEBELOW',(0,0),(-1,-1),.35,HexColor('#DCE5EB'))]))
    _,h=t.wrap(W-72,H); t.drawOn(c,36,H-y-9-h)
    return y+9+h+21

y=113
y=section(y,'01  Запуск и проверка XML',[
('main.py','Точка входа: запускает окно приложения.'),
('app/gui.py','Выбор файла, редактор, ошибки, подсказки, F5 и сохранение XML.'),
('app/validator.py','Парсинг XML, проверка XSD и формирование списка ошибок.'),
('app/schemas/people.xsd','Схема людей: общий тип, студент и сотрудник через наследование.'),
('app/schemas/books.xsd','Схема книг: название, автор и дата публикации.')])
y=section(y,'02  Данные и вспомогательные модули',[
('app/models.py','ORM-модель Book: описание таблицы книг в БД.'),
('app/db.py','Подключение к SQLite, сессии и создание таблиц.'),
('app/repository.py','Преобразование XML в Book и сохранение книг транзакцией.'),
('books.db','Файл SQLite с сохранёнными книгами.'),
('app/logger.py / log/app_log','Настройка логирования / файл журнала событий.'),
('app/valid1.py','Пробный скрипт логирования; не входит в основной сценарий.')])
y=section(y,'03  Примеры, тесты и документация',[
('examples/*.xml','Корректные и ошибочные XML для проверки приложения.'),
('tests/test_validation.py','Автотесты схем, диагностики, кодировок и импорта книг.'),
('tests/test_gui.py','Автотесты открытия, исправления и сохранения в интерфейсе.'),
('test_validator.py','Ручная проверка валидатора на трёх XML-сценариях.'),
('test_db_manual.py','Ручная проверка создания таблицы books.'),
('test_full.py','Ручной цикл: XML → валидация → сохранение книг в БД.'),
('requirements.txt','Список Python-зависимостей проекта и их версий.'),
('README.md / README.txt','Инструкция по запуску / указатель на документацию.'),
('docs/people-schema.md','Описание типов, полей и ограничений схемы людей.'),
('docs/project-review.md','Анализ проекта, текущие возможности и дальнейшие задачи.')])
assert y<798, y
c.showPage()

def code_block(y, source, font_size=7.3, leading=8.9, bad_line=None):
    lines = source.strip().splitlines()
    height = len(lines) * leading + 18
    c.setFillColor(HexColor('#F5F8FA'))
    c.roundRect(36, H-y-height, W-72, height, 5, fill=1, stroke=0)
    for number, line_text in enumerate(lines, 1):
        color = red if number == bad_line else ink
        text(45, y+12+(number-1)*leading, line_text, font_size, 'Consolas', color)
    return y+height

schema_text = (ROOT / 'app/schemas/people.xsd').read_text(encoding='utf-8-sig')
header(3,'XSD-схема People','Общий тип PersonType и наследники StudentType, EmployeeType.')
end = code_block(112, schema_text, font_size=7.1, leading=9.1)
assert end < 785, end
c.showPage()

valid_bytes = (ROOT / 'examples/people_valid.xml').read_bytes()
invalid_bytes = (ROOT / 'examples/people_invalid_email.xml').read_bytes()
schema = etree.XMLSchema(etree.parse(str(ROOT / 'app/schemas/people.xsd')))
assert schema.validate(etree.fromstring(valid_bytes))
assert not schema.validate(etree.fromstring(invalid_bytes))
assert len(schema.error_log) == 1
invalid_line = next(i for i, line_text in enumerate(invalid_bytes.decode('utf-8-sig').splitlines(), 1)
                    if 'ivan-at-example.org' in line_text)
header(4,'Примеры валидации','Одинаковая структура XML, разный результат проверки email.')
text(36,112,'ВЕРНЫЙ XML  /  examples/people_valid.xml',10,'ArialBold',green)
end_good = code_block(120, valid_bytes.decode('utf-8-sig'), font_size=7.2, leading=9.0)
text(36,end_good+18,'Результат: валидация пройдена. Студент и сотрудник соответствуют XSD.',9,'Arial',green)
start_bad = end_good + 41
text(36,start_bad,'НЕВЕРНЫЙ XML  /  examples/people_invalid_email.xml',10,'ArialBold',red)
end_bad = code_block(start_bad+8, invalid_bytes.decode('utf-8-sig'), font_size=7.2, leading=9.0, bad_line=invalid_line)
text(36,end_bad+18,'Результат: ошибка шаблона email на строке ' + str(invalid_line) + '.',9,'Arial',red)
text(36,end_bad+33,'Исправление: заменить ivan-at-example.org на ivan@example.org и нажать F5.',9)
assert end_bad+33 < 793, end_bad
c.save()
r=PdfReader(str(OUT)); assert len(r.pages)==4
for page in r.pages:
    assert abs(float(page.mediabox.width)-W)<1
    assert abs(float(page.mediabox.height)-H)<1
    assert len(page.extract_text())>500
print(OUT)
print('Verified: 4 A4 pages; page 3 bottom',end,'page 4 bottom',end_bad+33)
