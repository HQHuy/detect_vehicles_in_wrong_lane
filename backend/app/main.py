from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import routes
import os
import asyncio
import time
from app.db.database import engine, Base
from app.db import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hệ thống Nhận diện Xe Sai Làn")

# Cho phép Frontend ở cổng localhost:5173 (React Vite) gọi lên API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình trả file tĩnh (video output) ra ngoài cho web đọc được
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Đăng ký các API logic từ file routes.py
app.include_router(routes.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Hệ thống Nhận diện Xe Sai Làn đã hoạt động"}

@app.on_event("startup")
async def start_garbage_collection():
    async def cleanup_loop():
        while True:
            await asyncio.sleep(4 * 3600)  # Run every 4 hours
            try:
                now = time.time()
                retention_period = 3 * 86400  # 3 days
                
                # Cleanup captures
                cap_dir = os.path.join(static_dir, "captures")
                if os.path.exists(cap_dir):
                    for filename in os.listdir(cap_dir):
                        path = os.path.join(cap_dir, filename)
                        if os.path.isfile(path) and os.stat(path).st_mtime < now - retention_period:
                            os.remove(path)
                
                # Cleanup logs
                log_dir = os.path.join(static_dir, "logs")
                if os.path.exists(log_dir):
                    for filename in os.listdir(log_dir):
                        path = os.path.join(log_dir, filename)
                        if os.path.isfile(path) and os.stat(path).st_mtime < now - retention_period:
                            os.remove(path)
            except Exception as e:
                pass

    asyncio.create_task(cleanup_loop())
