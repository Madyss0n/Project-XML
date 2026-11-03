from datetime import datetime
from lxml import etree
from sqlalchemy.orm import Session
from app.models import Book
from app.logger import setup_logger

logger = setup_logger(__name__)

NS = {"b": "http://mephi3.ru"}


def parse_books_from_xml(root: etree._Element) -> list[Book]: #берет уже провалидированное дерево и превращает его в список объектов book, 
    """
    Превращает провалидированное XML-дерево в список объектов Book.
    Предполагается, что root уже прошёл validate_xml() и соответствует схеме,
    поэтому здесь не дублируем проверки структуры.
    """
    books = []
    for book_el in root.findall("b:book", namespaces=NS):
        name = book_el.find("b:name", namespaces=NS).text
        author = book_el.find("b:author", namespaces=NS).text
        publish_date_raw = book_el.find("b:publishDate", namespaces=NS).text

        publish_date = datetime.strptime(publish_date_raw, "%Y-%m-%d").date()

        books.append(Book(name=name, author=author, publish_date=publish_date))

    logger.info(f"Из XML извлечено записей: {len(books)}")
    return books


def save_books(session: Session, books: list[Book]) -> None:
    """Сохраняет список книг в БД одной транзакцией."""
    try:
        session.add_all(books)
        session.commit()
        logger.info(f"Сохранено в БД записей: {len(books)}")
    except Exception as e:
        session.rollback()
        logger.exception("Ошибка при сохранении в БД")
        raise