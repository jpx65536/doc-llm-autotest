# app/services/doc_check_service.py
from __future__ import annotations
import json
import os
from typing import Optional, Dict, Any
import redis
from app.services import task_service
from app.common.models import TaskStatus, TaskDocLLM

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    password=REDIS_PASSWORD,
)

TASK_QUEUE_READY_KEY = "doc_llm:task_queue:ready"


class TaskNotFoundError(Exception):
    """任务不存在"""
    pass


class InvalidTaskStatusError(Exception):
    """当前状态不允许重试"""
    pass


def submit_doc_task(task_name: str, doc: str, product: str | None, feature: str | None) -> int:
    """
    提交一个文档检查任务：
    1）在 MySQL 中创建任务（pending）
    2）往 Redis 队列写入任务消息
    3）返回 task_id
    """
    task: TaskDocLLM = task_service.create_task(task_name, doc, product, feature)

    payload = {
        "task_id": task.task_id,
        "task_name": task_name,
    }
    redis_client.lpush(TASK_QUEUE_READY_KEY, json.dumps(payload, ensure_ascii=False))

    return task.task_id


def retry_task(task_id: int) -> TaskDocLLM:
    """校验任务存在 & 状态为 failed，将任务状态改回 pending，再次推入 Redis 队列"""
    task: TaskDocLLM = task_service.get_task_by_id(task_id)
    if not task:
        raise TaskNotFoundError(f"任务 {task_id} 不存在")
    
    if task.status != TaskStatus.failed:
        raise InvalidTaskStatusError(f"任务 {task_id} 当前状态为 {task.status}，不允许重试")
    
    retry_result = task_service.mark_task_pending(task_id)
    if not retry_result:
        raise Exception(f"任务 {task_id} 重试失败，更新状态出错")

    payload = {
        "task_id": task_id,
        "task_name": task.task_name,
    }
    redis_client.lpush(TASK_QUEUE_READY_KEY, json.dumps(payload, ensure_ascii=False))

    return task


def get_task_detail(task_id: int) -> Optional[Dict[str, Any]]:
    """获取任务详情"""
    task = task_service.get_task_by_id(task_id)
    if not task:
        return None

    return {
        "task_id": task.task_id,
        "task_name": task.task_name,
        "create_time": task.create_time.isoformat() if task.create_time else None,
        "doc": task.doc,
        "status": task.status,
        "result": task.result,
    }


def list_all_tasks() -> list[dict]:
    """获取所有任务"""
    tasks = task_service.get_all_tasks()
    return [
        {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "create_time": task.create_time.isoformat() if task.create_time else None,
            "doc": task.doc,
            "status": task.status,
            "result": task.result,
            "product": task.product,
            "feature": task.feature,
        }
        for task in tasks
    ]


def delete_tasks(task_ids: list[int]) -> int:
    """删除指定任务ID的任务，返回删除的任务数量"""
    return task_service.delete_tasks(task_ids)


def update_task_doc(task_id: int, doc: str) -> None:
    """更新任务的 doc 字段"""
    task = task_service.get_task_by_id(task_id)
    if not task:
        raise TaskNotFoundError(f"任务 {task_id} 不存在")
    
    task_service.update_task_doc(task_id, doc)