from pydantic import BaseModel
from typing import Dict, List, Any

class SessionResponse(BaseModel):
    status: str
    session_id: str

class CaptureItem(BaseModel):
    id: int
    type: str
    event: str
    time: str
    image_url: str

class StatsResponse(BaseModel):
    stats: Dict[str, int]
    captures: List[CaptureItem]
    finished: bool
    csv_url: str

class StopStreamResponse(BaseModel):
    status: str
    message: str
