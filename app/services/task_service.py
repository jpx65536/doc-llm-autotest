# app/services/task_service.py
from __future__ import annotations
from typing import Optional
from sqlalchemy import select, delete
from app.common.db import get_session
from app.common.models import TaskDocLLM, TaskStatus


def create_task(task_name: str, doc: str) -> TaskDocLLM:
    """创建新的文档检查任务"""
    with get_session() as session:
        new_task = TaskDocLLM(
            task_name=task_name,
            doc=doc,
            status=TaskStatus.pending,
        )
        session.add(new_task)
        session.flush()
        return new_task
    

def get_task_by_id(task_id: int) -> Optional[TaskDocLLM]:
    """根据任务ID获取任务"""
    with get_session() as session:
        task = session.scalar(
            select(TaskDocLLM).where(TaskDocLLM.task_id == task_id)
        )
        return task
    

def get_all_tasks() -> list[TaskDocLLM]:
    """获取所有任务"""
    with get_session() as session:
        tasks = session.scalars(
            select(TaskDocLLM).order_by(TaskDocLLM.create_time.desc())
        ).all()
        return tasks
    

def update_task_status(
    task_id: int, 
    status: TaskStatus, 
    result: Optional[dict] = None
) -> bool:
    """更新任务状态和结果"""
    with get_session() as session:
        task = session.scalar(
            select(TaskDocLLM).where(TaskDocLLM.task_id == task_id)
        )
        if not task:
            return False

        task.status = status
        if result is not None:
            task.result = result
    return True


def delete_tasks(task_ids: list[int]) -> int:
    """删除指定任务ID的任务，返回删除的任务数量"""
    if not task_ids:
        return 0
    with get_session() as session:
        result = session.execute(
            delete(TaskDocLLM).where(TaskDocLLM.task_id.in_(task_ids))
        )
        return result.rowcount