# app/worker/doc_loader.py
import logging
from typing import Tuple

from app.services import file_service

PENDING_MARK = "__PENDING_FILE__"


class DocPendingError(Exception):
    """任务的 doc 还是占位符，文件还没就绪"""
    pass


class DocPathError(Exception):
    """doc 字段格式不合法"""
    pass


def _is_minio_path(doc: str) -> bool:
    """
    判断 doc 是否为 MinIO 路径：
      - /bucket/object_name
      - minio://bucket/object_name
    """
    if not doc:
        return False
    doc = doc.strip()
    return doc.startswith("/") or doc.startswith("minio://")


def _parse_minio_path(doc: str) -> Tuple[str, str]:
    """解析 doc 字段为 (bucket, object_name)"""
    s = doc.strip()

    if s.startswith("minio://"):
        _, rest = s.split("://", 1)
    else:
        rest = s.lstrip("/")
    if "/" not in rest:
        raise DocPathError(f"invalid minio doc path: {doc}")
    
    bucket, object_name = rest.split("/", 1)
    return bucket, object_name


def load_doc_for_task(task) -> str:
    """
    根据任务对象，返回真正要给 LLM 的 doc 文本（str）
    1. doc == "__PENDING_FILE__"        -> 抛 DocPendingError
    2. doc 是 MinIO 路径 (/bucket/obj)   -> 从 MinIO 下载并 decode
    3. 其他                             -> 当作普通文本直接返回
    """
    doc = (task.doc or "").strip()
    if not doc:
        raise DocPathError(f"task {task.task_id} doc is empty")
    
    if doc == PENDING_MARK:
        raise DocPendingError(f"task {task.task_id} doc is still pending file upload")
    
    if _is_minio_path(doc):
        bucket, object_name = _parse_minio_path(doc)
        logging.info(
            f"task {task.task_id} doc is minio path, bucket={bucket}, object={object_name}"
        )
        content_bytes = file_service.download_file(bucket, object_name)
        return content_bytes.decode("utf-8", errors="replace")
    
    return doc