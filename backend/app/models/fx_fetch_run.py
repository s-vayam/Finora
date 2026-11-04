from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, func
from app.database import Base


class FxFetchRun(Base):
    __tablename__ = "fx_fetch_runs"

    fetch_id = Column(String(50), primary_key=True, index=True)
    provider = Column(String(50), nullable=False, index=True)  # EXCHANGERATE_DEV, RBI_FBIL_ARCHIVE
    requested_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, index=True)  # SUCCESS, FAILED, PARTIAL, RUNNING
    request_count = Column(Integer, nullable=False, default=1)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    response_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<FxFetchRun {self.fetch_id}: {self.provider} [{self.status}] at {self.requested_at}>"

