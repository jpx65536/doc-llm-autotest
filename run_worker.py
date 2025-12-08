# run_worker.py
import logging
import threading
from app.llm import init_llm
from app.worker.doc_llm_test_worker import worker_loop
from app.worker.task_reaper import reaper_loop


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def start_reaper_thread():
    reaper_thread = threading.Thread(target=reaper_loop, name="doc_llm_reaper", daemon=True)
    reaper_thread.start()
    return reaper_thread

if __name__ == "__main__":
    setup_logging()
    init_llm()
    start_reaper_thread()
    worker_loop()