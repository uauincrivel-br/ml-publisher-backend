from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String, default="Operador")
    plan = Column(String, default="starter")
    created_at = Column(DateTime, default=datetime.utcnow)


class MLAccount(Base):
    __tablename__ = "ml_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    seller_id = Column(String, index=True)
    nickname = Column(String)
    client_id = Column(String)
    client_secret = Column(String)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_user_id = Column(String)
    connected = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    import_id = Column(String, index=True)
    offset = Column(Integer, index=True)
    sku = Column(String, index=True)
    title = Column(String)
    category_id = Column(String)
    price = Column(Float)
    stock = Column(Integer)
    raw_json = Column(Text)
    validation_status = Column(String, default="pending")
    validation_reason = Column(Text)
    item_id = Column(String, index=True)
    publication_status = Column(String, default="not_published")
    created_at = Column(DateTime, default=datetime.utcnow)


class PublishedItem(Base):
    __tablename__ = "published_items"

    id = Column(Integer, primary_key=True)
    seller_id = Column(String, index=True)
    sku = Column(String, unique=True, index=True)
    offset = Column(Integer, unique=True, index=True)
    item_id = Column(String, index=True)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class PublishQueue(Base):
    __tablename__ = "publish_queue"

    id = Column(Integer, primary_key=True)
    seller_id = Column(String, index=True)
    sku = Column(String, index=True)
    offset = Column(Integer, index=True)
    status = Column(String, default="queued")
    attempts = Column(Integer, default=0)
    last_error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    action = Column(String)
    sku = Column(String)
    offset = Column(Integer)
    item_id = Column(String)
    status = Column(String)
    detail = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)