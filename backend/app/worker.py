import time
import json
import requests
import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from datetime import datetime

from backend.app.database import SessionLocal
from backend.app.models.models import PublishQueue, Product, PublishedItem


# =========================================================
# WORKER CONFIG
# =========================================================
POLL_INTERVAL = 3  # segundos
MAX_ATTEMPTS = 3


# =========================================================
# SIMULAÇÃO DE PUBLICAÇÃO (DRY RUN)
# =========================================================
def simulate_ml_publish(product: Product):
    """
    Simula payload do Mercado Livre (SEM ENVIO REAL)
    """
    payload = {
        "title": product.title,
        "price": product.price,
        "category_id": product.category_id,
        "available_quantity": product.stock,
        "condition": "new",
        "currency_id": "BRL",
    }

    # Simulação de resposta do ML
    response = {
        "status": "success",
        "item_id": f"MLB{int(time.time())}",
        "payload_sent": payload,
    }

    return response


# =========================================================
# PROCESSAMENTO DE UMA FILA
# =========================================================
def process_queue_item(db, job: PublishQueue):
    try:
        product = db.query(Product).filter(
            Product.sku == job.sku,
            Product.offset == job.offset
        ).first()

        if not product:
            job.status = "error"
            job.last_error = "Produto não encontrado"
            job.attempts += 1
            db.commit()
            return

        # marca como processando
        job.status = "processing"
        db.commit()

        # SIMULA PUBLICAÇÃO
        result = simulate_ml_publish(product)

        # salva como publicado
        published = PublishedItem(
            seller_id=job.seller_id,
            sku=product.sku,
            offset=product.offset,
            item_id=result["item_id"],
            status="published"
        )

        db.add(published)

        # atualiza produto
        product.item_id = result["item_id"]
        product.publication_status = "published"

        # finaliza job
        job.status = "success"
        job.attempts += 1
        job.last_error = None

        db.commit()

        print(f"[OK] Publicado SKU={product.sku} ITEM={result['item_id']}")

    except Exception as e:
        job.status = "error"
        job.attempts += 1
        job.last_error = str(e)

        db.commit()

        print(f"[ERROR] SKU={job.sku} -> {str(e)}")


# =========================================================
# LOOP PRINCIPAL
# =========================================================
def run_worker():
    print("🚀 WORKER INICIADO - PROCESSANDO FILA...")

    db = SessionLocal()

    while True:
        try:
            jobs = db.query(PublishQueue).filter(
                PublishQueue.status == "queued"
            ).limit(5).all()

            if not jobs:
                time.sleep(POLL_INTERVAL)
                continue

            for job in jobs:
                process_queue_item(db, job)

        except Exception as e:
            print(f"[WORKER ERROR] {str(e)}")
            time.sleep(5)


# =========================================================
# START
# =========================================================
if __name__ == "__main__":
    run_worker()