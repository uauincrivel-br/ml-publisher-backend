import os
import time
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import pandas as pd
import requests

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# =========================================================
# CONFIG
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "mlp-v5-secret")

if not DATABASE_URL:
    raise Exception("DATABASE_URL não definida")

# =========================================================
# ENGINE (CORRIGIDO PRODUÇÃO RENDER)
# =========================================================

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

# =========================================================
# APP
# =========================================================

app = FastAPI(title="ML Publisher Enterprise V5", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ml-publisher-enterprise-v5",
        "environment": os.getenv("APP_ENV", "local")
    }

# =========================================================
# DB DEP
# =========================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================================================
# AUTH (JWT BLINDADO)
# =========================================================

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

def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_token")

    try:
        token = authorization.split(" ")[1]
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid_token: {str(e)}")

# =========================================================
# LOGIN TEST (TEMPORÁRIO)
# =========================================================

@app.post("/api/auth/login")
def login():
    return {
        "token": create_token(1, "admin@admin.com")
    }

# =========================================================
# UPLOAD (FIX PRODUÇÃO)
# =========================================================

@app.post("/api/import/upload")
def upload(file: UploadFile = File(...), user=Depends(get_current_user)):

    path = f"/tmp/{file.filename}"

    with open(path, "wb") as f:
        f.write(file.file.read())

    df = pd.read_excel(path)

    return {
        "ok": True,
        "rows": len(df),
        "columns": list(df.columns)
    }