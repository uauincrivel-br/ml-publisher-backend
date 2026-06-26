
import os
import time
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import pandas as pd
import requests
from backend.app.core.redis import product_queue

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.redis import product_queue

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "mlp-v5-secret")

if not DATABASE_URL:
    raise Exception("DATABASE_URL não definida")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI(title="ML Publisher Enterprise V5", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

@app.get("/api/health")
def health():
    return {"status": "ok"}

def create_token(user_id: int, email: str):
    return jwt.encode(
        {
            "sub": email,
            "uid": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        },
        JWT_SECRET,
        algorithm="HS256"
    )

@app.post("/api/auth/login")
def login():
    return {"token": create_token(1, "admin@admin.com")}

@app.post("/api/import/upload")
def upload(
    file: UploadFile = File(...),
    token: str = Depends(get_current_token)
):

    path = f"/tmp/{file.filename}"

    with open(path, "wb") as f:
        f.write(file.file.read())

    df = pd.read_excel(path)

    job_data = {
        "file_path": path,
        "token": token
    }

    job = product_queue.enqueue(
        "app.workers.product_worker.process_product_job",
        job_data
    )

    return {
        "ok": True,
        "rows": len(df),
        "job_id": job.id,
        "status": "queued"
    }
