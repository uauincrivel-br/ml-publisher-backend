import os
import time
import json
import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import pandas as pd
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# =========================================================
# DATABASE CONFIG (CORRIGIDO PARA SAAS)
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL não definida no ambiente")

# ✔ ENGINE CORRIGIDO (PRODUÇÃO + FALLBACK SQLITE)
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =========================================================
# APP
# =========================================================

APP_ENV = os.getenv("APP_ENV", "local")
JWT_SECRET = os.getenv("JWT_SECRET", "troque-este-segredo")

app = FastAPI(
    title="ML Publisher Enterprise V5 API",
    version="5.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# MODELS (IMPORTAÇÃO)
# =========================================================

from backend.app.models.models import (
    User,
    MLAccount,
    Product,
    PublishedItem,
    PublishQueue,
    AuditLog,
)

# =========================================================
# DEPENDENCY
# =========================================================

def db_dep():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================================================
# SECURITY
# =========================================================

def hash_pw(password: str) -> str:
    return hashlib.sha256(("mlp-v5:" + password).encode()).hexdigest()

def token_for(user: User) -> str:
    return jwt.encode(
        {
            "sub": user.email,
            "uid": user.id,
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        },
        JWT_SECRET,
        algorithm="HS256",
    )

def current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(db_dep),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization")

    token = authorization.replace("Bearer ", "").strip()

    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"jwt_error: {str(e)}")

    user = db.query(User).filter(User.id == data["uid"]).first()

    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")

    return user

# =========================================================
# HEALTHCHECK
# =========================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ml-publisher-enterprise-v5",
        "environment": APP_ENV,
    }