import os
import time
import json
import requests
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import (
    PublishQueue,
    PublishedItem,
    Product,
    MLAccount,
    User,
    AuditLog
)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(bind=engine, autoflush=False)

def log(db, user_id, action, status, detail="", sku=None, offset=None, item_id=None):
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        status=status,
        detail=detail,
        sku=sku,
        offset=offset,
        item_id=item_id,
        created_at=datetime.utcnow()
    ))
    db.commit()


def process_job(db, job):
    try:
        acc = db.query(MLAccount).filter(
            MLAccount.user_id == job.seller_id,
            MLAccount.seller_id == job.seller_id
        ).first()

        if not acc or not acc.access_token:
            job.status = "error"
            job.last_error = "token_missing"
            db.commit()
            return

        product = db.query(Product).filter(
            Product.user_id == job.seller_id,
            Product.sku == job.sku
        ).first()

        if not product:
            job.status = "error"
            job.last_error = "product_not_found"
            db.commit()
            return

        payload = {
            "title": product.title[:60],
            "category_id": product.category_id,
            "price": product.price,
            "currency_id": "BRL",
            "available_quantity": product.stock,
            "buying_mode": "buy_it_now",
            "condition": "new",
            "listing_type_id": "gold_special",
            "status": "paused"
        }

        r = requests.post(
            "https://api.mercadolibre.com/items",
            headers={"Authorization": f"Bearer {acc.access_token}"},
            json=payload,
            timeout=30
        )

        data = r.json() if r.text else {}

        if r.status_code >= 300:
            job.attempts += 1
            job.last_error = r.text[:500]
            job.status = "retry" if job.attempts < 3 else "error"
            db.commit()
            return

        item_id = data.get("id")

        product.item_id = item_id
        product.publication_status = "published_paused"

        db.add(PublishedItem(
            seller_id=str(job.seller_id),
            sku=job.sku,
            offset=job.offset,
            item_id=item_id,
            status="paused"
        ))

        job.status = "done"
        db.commit()

        log(db, job.seller_id, "worker_publish", "ok", json.dumps(data)[:500], job.sku, job.offset, item_id)

    except Exception as e:
        job.status = "error"
        job.last_error = str(e)
        db.commit()


def run_worker():
    print("WORKER STARTED...")

    db = SessionLocal()

    while True:
        jobs = db.query(PublishQueue).filter(
            PublishQueue.status.in_(["queued", "retry"])
        ).order_by(PublishQueue.id.asc()).limit(5).all()

        if not jobs:
            time.sleep(5)
            continue

        for job in jobs:
            job.status = "processing"
            db.commit()

            process_job(db, job)

            time.sleep(2)


if __name__ == "__main__":
    run_worker()