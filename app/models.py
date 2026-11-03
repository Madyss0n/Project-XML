from sqlalchemy import Column, Integer, String, Date, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    author = Column(String, nullable=False)
    publish_date = Column(Date, nullable=False)

    def __repr__(self):
        return f"<Book(name={self.name!r}, author={self.author!r}, publish_date={self.publish_date})>"


class ValidationErrorRecord(Base):
    """One diagnostic per row; validation_id groups a failed validation attempt."""
    __tablename__ = "validation_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    validation_id = Column(String(36), nullable=False, index=True)
    occurred_at = Column(DateTime, nullable=False, index=True)  # UTC
    source_name = Column(Text, nullable=False)
    schema_path = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    line = Column(Integer, nullable=False)
    column = Column(Integer, nullable=False)
    xpath = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=False)


class ValidationAccessRecord(Base):
    """One book or person from a successfully validated document."""
    __tablename__ = "validation_acces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    validation_id = Column(String(36), nullable=False, index=True)
    occurred_at = Column(DateTime, nullable=False, index=True)  # UTC
    source_name = Column(Text, nullable=False)
    schema_path = Column(Text, nullable=False)
    record_type = Column(String(30), nullable=False)  # book, student, employee

    # Book fields. Dates keep their XML spelling, including a possible timezone.
    name = Column(Text)
    author = Column(Text)
    publish_date = Column(Text)

    # Common person fields and the two subclasses from people.xsd.
    person_id = Column(Text)
    full_name = Column(Text)
    birth_date = Column(Text)
    email1 = Column(Text)
    email2 = Column(Text)
    email3 = Column(Text)
    phone = Column(Text)
    university = Column(Text)
    course = Column(Integer)
    organization = Column(Text)
    position = Column(Text)
