"""SQLAlchemy models for HANDOFF data."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Meta(Base):
    """Key-value store for vision, agent roles, sections (markdown or text)."""
    __tablename__ = "meta"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)


class Phase(Base):
    """One phase/task unit (e.g. D-1, E-2). Status is commit-driven or agent-updated."""
    __tablename__ = "phases"
    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(String(32), unique=True, nullable=False, index=True)  # D-1, E-2
    title = Column(String(256), nullable=True)
    status = Column(String(32), default="待办")  # 待办|进行中|待审核|需修改|已完成
    pr_url = Column(String(512), nullable=True)
    note = Column(Text, nullable=True)
    assignee = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tasks = relationship("PhaseTask", back_populates="phase", cascade="all, delete-orphan")


class PhaseTask(Base):
    """Checklist item under a phase (e.g. '新建 reporter.py')."""
    __tablename__ = "phase_tasks"
    id = Column(Integer, primary_key=True, index=True)
    phase_id = Column(Integer, ForeignKey("phases.id"), nullable=False)
    content = Column(Text, nullable=False)
    done = Column(Boolean, default=False)
    phase = relationship("Phase", back_populates="tasks")


class CurrentTask(Base):
    """Current todo table: assignee, task description, launch command."""
    __tablename__ = "current_tasks"
    id = Column(Integer, primary_key=True, index=True)
    assignee = Column(String(64), nullable=True)
    task_desc = Column(Text, nullable=False)
    launch_cmd = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)


class LaunchInstruction(Base):
    """Launch instruction block per agent type (backend, ios, test)."""
    __tablename__ = "launch_instructions"
    id = Column(Integer, primary_key=True, index=True)
    agent_type = Column(String(32), unique=True, nullable=False, index=True)
    body = Column(Text, nullable=False)


class CompletionLog(Base):
    """Completion / update log entries."""
    __tablename__ = "completion_log"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
