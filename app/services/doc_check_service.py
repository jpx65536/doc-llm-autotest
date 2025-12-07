# app/services/doc_check_service.py
from __future__ import annotations
import json
from typing import Optional, Dict, Any
import redis
from app.services import task_service
from app.common.models import TaskStatus, TaskDocLLM


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    password="xiao1234",
)

TASK_QUEUE_KEY = "doc_llm:task_queue"


def submit_doc_task(task_name: str, doc: str) -> int:
    """
    提交一个文档检查任务：
    1）在 MySQL 中创建任务（pending）
    2）往 Redis 队列写入任务消息
    3）返回 task_id
    """
    task: TaskDocLLM = task_service.create_task(task_name, doc)

    payload = {
        "task_id": task.task_id,
        "task_name": task_name,
    }
    redis_client.lpush(TASK_QUEUE_KEY, json.dumps(payload, ensure_ascii=False))

    return task.task_id


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
        }
        for task in tasks
    ]


def delete_tasks(task_ids: list[int]) -> int:
    """删除指定任务ID的任务，返回删除的任务数量"""
    return task_service.delete_tasks(task_ids)