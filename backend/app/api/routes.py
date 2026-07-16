from fastapi import APIRouter, UploadFile, File, Form, Depends
from pydantic import BaseModel
from fastapi.responses import JSONResponse, StreamingResponse
import shutil
import json
import os
import uuid
from datetime import datetime
from app.services.model_service import ModelService
from app.schemas import SessionResponse, StatsResponse, StopStreamResponse

router = APIRouter()

class PolygonUpdate(BaseModel):
    mode: int = 0
    car: list = []
    moto: list = []
    wrongway_down: list = []
    wrongway_up: list = []

# LƯU GLOBAL STATE API
SESSION_DATA = {}

# Lưu 1 instance toàn cục của ModelService để tránh việc nạp weight model (YOLO) nhiều lần
_model_service_instance = ModelService()

def get_model_service():
    return _model_service_instance

@router.post("/prepare_stream/", response_model=SessionResponse)
async def prepare_stream(
    file: UploadFile = File(...),
    poly_data: str = Form(...) 
):
    try:
        polygons = json.loads(poly_data)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "poly_data không hợp lệ", "detail": str(e)})

    # Lưu tạm Video gốc tải lên
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    upload_dir = os.path.join(base_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_video_path = os.path.join(upload_dir, f"raw_{timestamp}_{file.filename}")
    
    with open(temp_video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    session_id = str(uuid.uuid4())
    SESSION_DATA[session_id] = {
        "video_path": temp_video_path,
        "polygons": polygons,
        "stats": {'car': 0, 'moto': 0, 'bus': 0, 'truck': 0, 'motorcycle': 0},
        "captures": [],
        "is_running": False,
        "finished": False,
        "csv_url": "",
        "timestamp": timestamp
    }
    
    return {"status": "success", "session_id": session_id}

@router.get("/video_feed/{session_id}")
async def video_feed(session_id: str, service: ModelService = Depends(get_model_service)):
    if session_id not in SESSION_DATA:
        return JSONResponse(status_code=404, content={"error": "Session không tự tại."})
    
    session_dict = SESSION_DATA[session_id]
    
    return StreamingResponse(
        service.generate_frames(session_id, session_dict, session_dict["timestamp"]), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/stream_stats/{session_id}", response_model=StatsResponse)
async def stream_stats(session_id: str):
    if session_id not in SESSION_DATA:
        return JSONResponse(status_code=404, content={"error": "Not Found"})
    
    session_dict = SESSION_DATA[session_id]
    return {
        "stats": session_dict["stats"],
        "captures": session_dict.get("captures", []),
        "finished": session_dict["finished"],
        "csv_url": session_dict["csv_url"]
    }

@router.post("/stop_stream/{session_id}", response_model=StopStreamResponse)
async def stop_stream(session_id: str):
    if session_id in SESSION_DATA:
        SESSION_DATA[session_id]["is_running"] = False
        return StopStreamResponse(status="success", message="Stopped stream.")
    return JSONResponse(status_code=404, content={"error": "Not Found"})

@router.post("/pause_stream/{session_id}")
async def pause_stream(session_id: str):
    if session_id in SESSION_DATA:
        SESSION_DATA[session_id]["is_paused"] = True
        return {"status": "success", "message": "Paused stream."}
    return JSONResponse(status_code=404, content={"error": "Not Found"})

@router.post("/resume_stream/{session_id}")
async def resume_stream(session_id: str):
    if session_id in SESSION_DATA:
        SESSION_DATA[session_id]["is_paused"] = False
        return {"status": "success", "message": "Resumed stream."}
    return JSONResponse(status_code=404, content={"error": "Not Found"})

@router.post("/update_polygons/{session_id}")
async def update_polygons(session_id: str, payload: PolygonUpdate):
    if session_id in SESSION_DATA:
        SESSION_DATA[session_id]["polygons"] = payload.dict()
        return {"status": "success"}
    return JSONResponse(status_code=404, content={"error": "Not Found"})
