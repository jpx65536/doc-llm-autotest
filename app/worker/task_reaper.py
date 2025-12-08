# app/worker/task_reaper.py
import json
import logging
import time
import threading
import redis
import os
from datetime import datetime, timedelta

from app.services import task_service

TASK_QUEUE_READY_KEY = "doc_llm:task_queue:ready"
TASK_QUEUE_PROCESSING_KEY = "doc_llm:task_queue:processing"
TASK_PROCESSING_TS_KEY = "doc_llm:hash:processing_ts"

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    password=REDIS_PASSWORD,
)

PROCESSING_TIMEOUT_SECONDS = 600
REAPER_INTERVAL_SECONDS = 30


def reaper_loop():
    """巡检 processing 队列，恢复超时的任务"""
    logging.info("doc_llm_reaper started, interval=%ss, timeout=%ss", REAPER_INTERVAL_SECONDS, PROCESSING_TIMEOUT_SECONDS)
    while True:
        try:
            now_ts = int(time.time())
            timeout_border_ts = now_ts - PROCESSING_TIMEOUT_SECONDS
            timeout_threshold_dt = datetime.utcnow() - timedelta(seconds=PROCESSING_TIMEOUT_SECONDS)
            
            items = redis_client.lrange(TASK_QUEUE_PROCESSING_KEY, 0, -1)
            if not items:
                time.sleep(REAPER_INTERVAL_SECONDS)
                continue
            for raw in items:
                try:
                    payload_str = raw.decode("utf-8")
                    payload = json.loads(payload_str)
                    task_id = payload.get("task_id")
                    task_name = payload.get("task_name")
                except Exception:
                    redis_client.lrem(TASK_QUEUE_PROCESSING_KEY, 1, raw)
                    continue

                start_ts_raw = redis_client.hget(TASK_PROCESSING_TS_KEY, task_id)
                if start_ts_raw is None:
                    continue
                start_ts = int(start_ts_raw)
                if start_ts > timeout_border_ts:
                    continue
                logging.warning(f"doc_llm_reaper: task {task_id} seems stuck, start_ts={start_ts}, now_ts={now_ts}")

                ok = task_service.reclaim_task(task_id, timeout_threshold_dt)
                if not ok:
                    continue
                redis_client.lrem(TASK_QUEUE_PROCESSING_KEY, 1, raw)
                redis_client.hdel(TASK_PROCESSING_TS_KEY, task_id)

                new_payload = json.dumps(
                    {"task_id": task_id, "task_name": task_name}, ensure_ascii=False
                )
                redis_client.lpush(TASK_QUEUE_READY_KEY, new_payload)
                logging.info(f"doc_llm_reaper: task {task_id} reclaimed and requeued to READY")
        except Exception:
            logging.exception("unexpected error in reaper loop, sleep 3s")
        time.sleep(REAPER_INTERVAL_SECONDS)