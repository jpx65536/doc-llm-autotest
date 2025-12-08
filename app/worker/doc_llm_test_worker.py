# # app/worker/doc_llm_test_worker.py
import logging
import time
import redis
import json
import os

from app.services import task_service
from app.llm import run_doc_check_structured
from app.worker import doc_loader

TASK_QUEUE_KEY = "doc_llm:task_queue"

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    password=REDIS_PASSWORD,
)


def process_task(task_id: int):
    """处理文档检查任务"""
    logging.info(f"start process task {task_id}")
    task = task_service.get_pending_task(task_id)
    if not task:
        logging.warning(f"task {task_id} not found or not pending")
        return
    
    ok = task_service.mark_task_processing(task_id)
    if not ok:
        logging.warning(f"failed to mark task {task_id} as processing")
        return
    
    try:
        try:
            doc_text = doc_loader.load_doc_for_task(task)
        except doc_loader.DocPendingError as e:
            logging.info(f"task {task_id} doc pending, waiting...")
            try:
                task = wait_for_doc_ready(task_id)
                doc_text = doc_loader.load_doc_for_task(task)
            except Exception as e2:
                logging.error(f"task {task_id} pending wait failed: {e2}")
                task_service.mark_task_failed(task_id, str(e2))
                return
        except doc_loader.DocPathError as e:
            logging.error(f"task {task_id} invalid doc path: {e}")
            task_service.mark_task_failed(task_id, str(e))
            return
        
        doc = doc_text
        product = task.product
        feature = task.feature

        result = run_doc_check_structured(doc, product, feature)

        task_service.mark_task_success(task_id, result)
        logging.info(f"task {task_id} processed successfully")
    except Exception as e:
        logging.exception(f"task {task_id} failed: {repr(e)}")
        task_service.mark_task_failed(task_id, str(e))


def worker_loop():
    """文档检查任务 worker 主循环"""
    logging.info("doc_llm_test_worker started, waiting for tasks...")
    while True:
        try:
            item = redis_client.brpop(TASK_QUEUE_KEY, timeout=10)
            if not item:
                time.sleep(5)
                continue # 没有任务，就继续下一轮

            _queue_name, raw_value = item
            try:
                payload = raw_value.decode("utf-8")
                data = json.loads(payload)
                task_id = int(data["task_id"])
            except Exception as e:
                logging.exception(f"invalid queue item: {raw_value!r}")
                continue
            process_task(task_id)
        except Exception:
            logging.exception("unexpected error in worker loop, sleep 3s")
            time.sleep(3)
        

def wait_for_doc_ready(task_id: int):
    """
    当 doc == "__PENDING_FILE__" 时，等待 doc 字段被控制面更新。
    超过最大重试次数仍未更新则抛出异常。
    """
    PENDING_RETRY_INTERVAL = 2
    PENDING_RETRY_MAX = 5

    for i in range(PENDING_RETRY_MAX):
        time.sleep(PENDING_RETRY_INTERVAL)
        task = task_service.get_task_by_id(task_id)
        if not task:
            raise RuntimeError(f"task {task_id} disappeared during pending wait")
        
        doc = (task.doc or "").strip()
        if doc != doc_loader.PENDING_MARK:
            logging.info(f"task {task_id} doc is ready after {i+1} retries: {doc}")
            return task
        logging.info(f"task {task_id} doc still pending (retry {i+1}/{PENDING_RETRY_MAX})")

    raise RuntimeError(f"task {task_id} doc still pending after max retries")
