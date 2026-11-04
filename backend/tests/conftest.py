import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, get_db
from app.main import app
from app.services.data_import_service import DataImportService

@pytest.fixture(scope="session")
def raw_data_dir() -> Path:
    return BACKEND_DIR / "data" / "raw" / "finora_synthetic_data"

@pytest.fixture(scope="function")
def test_db_session() -> Generator[Session, None, None]:
    """Create a fresh temporary SQLite database for each test function."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    test_engine = create_engine(
        f"sqlite:///{tmp_db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        test_engine.dispose()
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except PermissionError:
                pass

@pytest.fixture(scope="function")
def client(test_db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient wired with isolated test database."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def seeded_test_db(test_db_session: Session, raw_data_dir: Path) -> Session:
    """Test database pre-seeded with synthetic financial dataset and backfilled payments."""
    service = DataImportService(data_dir=raw_data_dir, db=test_db_session)
    service.import_all(dry_run=False, force=False)
    from app.services.payment_backfill_service import PaymentBackfillService
    PaymentBackfillService(db=test_db_session).validate_and_backfill(dry_run=False, force=False)
    return test_db_session

@pytest.fixture(scope="function")
def seeded_client(seeded_test_db: Session) -> Generator[TestClient, None, None]:
    """TestClient wired with seeded test database."""
    def override_get_db():
        try:
            yield seeded_test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

