from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def isolate_history(test_case):
    """Keep automatic audit writes out of the user's books.db."""
    engine = create_engine('sqlite:///:memory:')
    factory = sessionmaker(bind=engine)
    test_case.addCleanup(engine.dispose)
    patcher = patch('app.validation_history.SessionLocal', factory)
    patcher.start()
    test_case.addCleanup(patcher.stop)
    return engine, factory
