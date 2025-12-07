# app/common/model.py
from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import JSON, BigInteger, String, Text, DateTime, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class TaskStatus(str, PyEnum):
    pending = "pending"
    processing = "processing"
    success = "success"
    failed = "failed"


class TaskDocLLM(Base):
    __tablename__ = "task_doc_llm"

    task_id: Mapped[int] = mapped_column(
        "task_id", BigInteger, primary_key=True, autoincrement=True, comment="任务ID，自增主键"
    )
    task_name: Mapped[str] = mapped_column(
        "task_name", String(255), nullable=False, comment="任务名称，可重复"
    )
    create_time: Mapped[datetime] = mapped_column(
        "create_time", DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    doc: Mapped[str] = mapped_column(
        "doc", String(length=65535), nullable=False, comment="文档内容"
    )
    product: Mapped[str | None] = mapped_column(
        "product", String(100), nullable=True, comment="产品名称"
    )
    feature: Mapped[str | None] = mapped_column(
        "feature", String(5000), nullable=True, comment="功能点"
    )
    status: Mapped[TaskStatus] = mapped_column(
        "status", Enum(TaskStatus), nullable=False, default=TaskStatus.pending, comment="任务状态"
    )
    result: Mapped[dict | None] = mapped_column(
        "result", JSON, nullable=True, comment="执行结果，JSON 格式，pending 时为 NULL",
    )
    __table_args__ = (
        Index("idx_status_ctime", "status", "create_time"),
    )
    def __repr__(self) -> str:
        return (
            f"<TaskDocLLM(task_id={self.task_id}, "
            f"name={self.task_name!r}, status={self.status})>"
        )
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "product": self.product,
            "feature": self.feature,
            "status": self.status,
            "result": self.result,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "doc": self.doc,
        }