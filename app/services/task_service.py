# app/services/task_service.py
from __future__ import annotations
from typing import Optional
from sqlalchemy import select, delete, update, func
from app.common.db import get_session
from app.common.models import TaskDocLLM, TaskStatus


def create_task(task_name: str, doc: str, product: str | None, feature: str | None) -> TaskDocLLM:
    """创建新的文档检查任务"""
    with get_session() as session:
        new_task = TaskDocLLM(
            task_name=task_name,
            doc=doc,
            product=product,
            feature=feature,
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
    

def mark_task_processing(task_id: int) -> bool:
    """worker 刚拿到任务时调用：pending -> processing"""
    with get_session() as session:
        stmt = (
            update(TaskDocLLM).where(
                TaskDocLLM.task_id == task_id,
                TaskDocLLM.status == TaskStatus.pending
            ).values(
                status=TaskStatus.processing,
                processing_started_at=func.now()
            )
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount == 1
    

def mark_task_success(task_id: int, result: dict) -> bool:
    """worker 任务成功完成时调用：processing -> success"""
    return update_task_status(task_id, TaskStatus.success, result)


def mark_task_failed(task_id: int, error_msg: str) -> bool:
    """任务失败 -> failed，把错误信息写进 result"""
    result = {
        "success": False,
        "error": error_msg,
    }
    return update_task_status(task_id, TaskStatus.failed, result)


def mark_task_pending(task_id: int) -> bool:
    """将任务状态改回 pending，用于重试"""
    with get_session() as session:
        task = session.scalar(
            select(TaskDocLLM).where(TaskDocLLM.task_id == task_id)
        )
        if not task:
            return False
        task.status = TaskStatus.pending
        task.result = None
    return True


def get_pending_task(task_id: int) -> Optional[TaskDocLLM]:
    """只返回 pending 状态的任务，其他状态直接 None"""
    with get_session() as session:
        task = session.scalar(
            select(TaskDocLLM).where(
                TaskDocLLM.task_id == task_id,
                TaskDocLLM.status == TaskStatus.pending,
            )
        )
        if not task:
            return None
        return task
    

def update_task_doc(task_id: int, doc: str) -> None:
    """更新任务的 doc 字段"""
    with get_session() as session:
        task = session.scalar(
            select(TaskDocLLM).where(TaskDocLLM.task_id == task_id)
        )
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
        task.doc = doc


def reclaim_task(task_id: int, timeout_dt) -> bool:
    """
    将超时的任务重新放回队列
    :param timeout_dt: datetime对象，代表“必须早于此时间才会被恢复”
    """
    with get_session() as session:
        stmt = (
            update(TaskDocLLM).where(
                TaskDocLLM.task_id == task_id,
                TaskDocLLM.status == TaskStatus.processing,
                TaskDocLLM.processing_started_at < timeout_dt
            ).values(
                status=TaskStatus.pending,
                retry_count=TaskDocLLM.retry_count + 1,
                processing_started_at=None,
                result=None
            )
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount == 1