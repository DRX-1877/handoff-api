"""Pydantic schemas for HANDOFF API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MetaOut(BaseModel):
    key: str
    value: Optional[str] = None


class PhaseTaskOut(BaseModel):
    id: int
    content: str
    done: bool

    class Config:
        from_attributes = True


class PhaseOut(BaseModel):
    id: int
    phase_id: str
    title: Optional[str] = None
    status: str
    pr_url: Optional[str] = None
    note: Optional[str] = None
    assignee: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tasks: list[PhaseTaskOut] = []

    class Config:
        from_attributes = True


class CurrentTaskOut(BaseModel):
    id: int
    assignee: Optional[str] = None
    task_desc: str
    launch_cmd: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class LaunchInstructionOut(BaseModel):
    id: int
    agent_type: str
    body: str

    class Config:
        from_attributes = True


class CompletionLogOut(BaseModel):
    id: int
    date: str
    message: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Repo commit for dashboard
class RepoCommitOut(BaseModel):
    message: str
    sha: str
    sha_full: str = ""
    date: str
    url: str = ""


# Full handoff response
class HandoffOut(BaseModel):
    meta: dict
    current_tasks: list[CurrentTaskOut]
    phases: list[PhaseOut]
    completion_log: list[CompletionLogOut]
    launch_instructions: list[LaunchInstructionOut]
    repo_commits: dict[str, list[RepoCommitOut]] = {}


# Write schemas
class PhaseCreate(BaseModel):
    phase_id: str
    title: Optional[str] = None
    assignee: Optional[str] = None


class PhaseUpdate(BaseModel):
    title: Optional[str] = None
    assignee: Optional[str] = None


class PhaseStatusUpdate(BaseModel):
    status: str  # 待办|进行中|待审核|需修改|已完成
    pr_url: Optional[str] = None
    note: Optional[str] = None


class PhaseTaskCreate(BaseModel):
    content: str
    done: bool = False


class CurrentTaskCreate(BaseModel):
    assignee: Optional[str] = None
    task_desc: str
    launch_cmd: Optional[str] = None
    sort_order: int = 0


class CurrentTaskUpdate(BaseModel):
    assignee: Optional[str] = None
    task_desc: Optional[str] = None
    launch_cmd: Optional[str] = None
    sort_order: Optional[int] = None


class LaunchInstructionUpdate(BaseModel):
    body: str


class CompletionLogCreate(BaseModel):
    date: str
    message: str
