# run_worker.py
import logging
from app.llm import init_llm
from app.worker.doc_llm_test_worker import worker_loop


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


if __name__ == "__main__":
    setup_logging()
    init_llm()
    worker_loop()