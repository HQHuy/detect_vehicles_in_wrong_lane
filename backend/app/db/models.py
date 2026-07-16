from sqlalchemy import Column, Integer, String, DateTime
from .database import Base
import datetime

class ViolationLog(Base):
    __tablename__ = "violation_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    session_id = Column(String, index=True)
    vehicle_id = Column(Integer, index=True)
    vehicle_type = Column(String)
    event_type = Column(String)
    capture_url = Column(String, nullable=True)
