from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(50), ForeignKey("invoices.invoice_id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_timestamp = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    model_version = Column(String(50), nullable=False)
    predicted_late_probability = Column(Float, nullable=False)
    risk_category = Column(String(20), nullable=False)
    predicted_delay_days = Column(Float, nullable=False)
    expected_delay_days = Column(Float, nullable=False)
    estimated_payment_date = Column(Date, nullable=False)
    features_snapshot = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    invoice = relationship("Invoice", back_populates="predictions")

    def __repr__(self) -> str:
        return (
            f"<MLPrediction id={self.id} invoice={self.invoice_id} "
            f"prob={self.predicted_late_probability:.2f} risk={self.risk_category}>"
        )
