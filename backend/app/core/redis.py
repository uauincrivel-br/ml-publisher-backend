import os
import redis
from rq import Queue

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise Exception("REDIS_URL não configurada")

redis_conn = redis.from_url(REDIS_URL)

product_queue = Queue("product_queue", connection=redis_conn)
