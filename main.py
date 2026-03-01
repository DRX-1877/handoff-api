"""HANDOFF API: read/write handoff state, status updates, optional GitHub webhook."""
import base64
import re
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import httpx

from database import engine, get_db, Base
from models import Meta, Phase, PhaseTask, CurrentTask, LaunchInstruction, CompletionLog
from schemas import (
    HandoffOut, PhaseOut, PhaseTaskOut, CurrentTaskOut,
    LaunchInstructionOut, CompletionLogOut,
    PhaseCreate, PhaseUpdate, PhaseStatusUpdate, PhaseTaskCreate,
    CurrentTaskCreate, CurrentTaskUpdate, LaunchInstructionUpdate, CompletionLogCreate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="HANDOFF API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/dashboard", response_class=FileResponse)
def dashboard():
    """Single-page HANDOFF dashboard (H-5)."""
    return FileResponse(_STATIC_DIR / "dashboard.html")


def meta_to_dict(db: Session) -> dict:
    rows = db.query(Meta).all()
    return {r.key: r.value for r in rows}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/handoff", response_model=HandoffOut)
def get_handoff(db: Session = Depends(get_db)):
    """Full handoff: meta, current_tasks, phases (with tasks), completion_log, launch_instructions."""
    meta = meta_to_dict(db)
    current_tasks = db.query(CurrentTask).order_by(CurrentTask.sort_order, CurrentTask.id).all()
    phases = db.query(Phase).order_by(Phase.id).all()
    completion_log = db.query(CompletionLog).order_by(CompletionLog.created_at.desc()).limit(50).all()
    launch_instructions = db.query(LaunchInstruction).order_by(LaunchInstruction.agent_type).all()
    return HandoffOut(
        meta=meta,
        current_tasks=current_tasks,
        phases=phases,
        completion_log=completion_log,
        launch_instructions=launch_instructions,
    )


@app.get("/handoff/meta")
def get_meta(db: Session = Depends(get_db)):
    return meta_to_dict(db)


@app.get("/handoff/current-tasks", response_model=list[CurrentTaskOut])
def get_current_tasks(db: Session = Depends(get_db)):
    return db.query(CurrentTask).order_by(CurrentTask.sort_order, CurrentTask.id).all()


@app.get("/handoff/phases", response_model=list[PhaseOut])
def get_phases(db: Session = Depends(get_db)):
    return db.query(Phase).order_by(Phase.id).all()


@app.get("/handoff/phases/{phase_id}", response_model=PhaseOut)
def get_phase(phase_id: str, db: Session = Depends(get_db)):
    phase = db.query(Phase).filter(Phase.phase_id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    return phase


@app.get("/handoff/completion-log", response_model=list[CompletionLogOut])
def get_completion_log(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(CompletionLog).order_by(CompletionLog.created_at.desc()).limit(limit).all()


@app.get("/handoff/launch-instructions", response_model=list[LaunchInstructionOut])
def get_launch_instructions(db: Session = Depends(get_db)):
    return db.query(LaunchInstruction).order_by(LaunchInstruction.agent_type).all()


@app.get("/handoff/launch-instructions/{agent_type}", response_model=LaunchInstructionOut)
def get_launch_instruction(agent_type: str, db: Session = Depends(get_db)):
    row = db.query(LaunchInstruction).filter(LaunchInstruction.agent_type == agent_type).first()
    if not row:
        raise HTTPException(status_code=404, detail="Launch instruction not found")
    return row


@app.get("/handoff/export")
def export_handoff(format: str = "markdown", db: Session = Depends(get_db)):
    """Export handoff as markdown (or json)."""
    if format != "markdown":
        raise HTTPException(status_code=400, detail="Only format=markdown supported")
    meta = meta_to_dict(db)
    current_tasks = db.query(CurrentTask).order_by(CurrentTask.sort_order, CurrentTask.id).all()
    phases = db.query(Phase).order_by(Phase.id).all()
    completion_log = db.query(CompletionLog).order_by(CompletionLog.created_at.desc()).limit(30).all()
    launch_instructions = db.query(LaunchInstruction).order_by(LaunchInstruction.agent_type).all()

    lines = ["# HANDOFF", ""]
    if meta.get("vision_quote"):
        lines.append("## 产品愿景（引用）")
        lines.append(meta["vision_quote"])
        lines.append("")
    if meta.get("vision_summary"):
        lines.append("## 愿景摘要")
        lines.append(meta["vision_summary"])
        lines.append("")
    lines.append("## 当前待办")
    lines.append("| 负责 | 任务 | 启动命令 |")
    lines.append("|------|------|----------|")
    for t in current_tasks:
        lines.append(f"| {t.assignee or ''} | {t.task_desc} | {t.launch_cmd or ''} |")
    lines.append("")
    lines.append("## Phases")
    for p in phases:
        lines.append(f"### {p.phase_id}：{p.title or ''}")
        lines.append(f"- 状态：{p.status}" + (f" | PR：{p.pr_url}" if p.pr_url else "") + (f" | {p.note}" if p.note else ""))
        for task in p.tasks:
            lines.append(f"- [{'x' if task.done else ' '}] {task.content}")
        lines.append("")
    lines.append("## 更新日志")
    for log in completion_log:
        lines.append(f"- **{log.date}** {log.message}")
    lines.append("")
    lines.append("## 启动指令")
    for li in launch_instructions:
        lines.append(f"### {li.agent_type}")
        lines.append("```")
        lines.append(li.body)
        lines.append("```")
        lines.append("")
    return {"format": "markdown", "content": "\n".join(lines)}


# ----- Write API -----

@app.put("/handoff/meta/{key}")
def set_meta(key: str, value: str, db: Session = Depends(get_db)):
    row = db.query(Meta).filter(Meta.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Meta(key=key, value=value))
    db.commit()
    return {"key": key, "value": value}


@app.post("/handoff/phases", response_model=PhaseOut)
def create_phase(body: PhaseCreate, db: Session = Depends(get_db)):
    if db.query(Phase).filter(Phase.phase_id == body.phase_id).first():
        raise HTTPException(status_code=400, detail="Phase id already exists")
    phase = Phase(phase_id=body.phase_id, title=body.title, assignee=body.assignee)
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase


@app.patch("/handoff/phases/{phase_id}")
def update_phase(phase_id: str, body: PhaseUpdate, db: Session = Depends(get_db)):
    phase = db.query(Phase).filter(Phase.phase_id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    if body.title is not None:
        phase.title = body.title
    if body.assignee is not None:
        phase.assignee = body.assignee
    db.commit()
    return {"phase_id": phase_id, "ok": True}


@app.patch("/handoff/phases/{phase_id}/status")
def update_phase_status(phase_id: str, body: PhaseStatusUpdate, db: Session = Depends(get_db)):
    phase = db.query(Phase).filter(Phase.phase_id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    phase.status = body.status
    if body.pr_url is not None:
        phase.pr_url = body.pr_url
    if body.note is not None:
        phase.note = body.note
    db.commit()
    return {"phase_id": phase_id, "status": phase.status}


@app.post("/handoff/phases/{phase_id}/tasks", response_model=PhaseTaskOut)
def create_phase_task(phase_id: str, body: PhaseTaskCreate, db: Session = Depends(get_db)):
    phase = db.query(Phase).filter(Phase.phase_id == phase_id).first()
    if not phase:
        raise HTTPException(status_code=404, detail="Phase not found")
    task = PhaseTask(phase_id=phase.id, content=body.content, done=body.done)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


class PhaseTaskDoneUpdate(BaseModel):
    done: bool


@app.patch("/handoff/phase-tasks/{task_id}")
def toggle_phase_task(task_id: int, body: PhaseTaskDoneUpdate, db: Session = Depends(get_db)):
    task = db.query(PhaseTask).filter(PhaseTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Phase task not found")
    task.done = body.done
    db.commit()
    return {"id": task_id, "done": task.done}


@app.post("/handoff/current-tasks", response_model=CurrentTaskOut)
def create_current_task(body: CurrentTaskCreate, db: Session = Depends(get_db)):
    task = CurrentTask(
        assignee=body.assignee,
        task_desc=body.task_desc,
        launch_cmd=body.launch_cmd,
        sort_order=body.sort_order,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.patch("/handoff/current-tasks/{task_id}", response_model=CurrentTaskOut)
def update_current_task(task_id: int, body: CurrentTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(CurrentTask).filter(CurrentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Current task not found")
    if body.assignee is not None:
        task.assignee = body.assignee
    if body.task_desc is not None:
        task.task_desc = body.task_desc
    if body.launch_cmd is not None:
        task.launch_cmd = body.launch_cmd
    if body.sort_order is not None:
        task.sort_order = body.sort_order
    db.commit()
    db.refresh(task)
    return task


@app.delete("/handoff/current-tasks/{task_id}")
def delete_current_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(CurrentTask).filter(CurrentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Current task not found")
    db.delete(task)
    db.commit()
    return {"deleted": task_id}


@app.put("/handoff/launch-instructions/{agent_type}")
def set_launch_instruction(agent_type: str, body: LaunchInstructionUpdate, db: Session = Depends(get_db)):
    row = db.query(LaunchInstruction).filter(LaunchInstruction.agent_type == agent_type).first()
    if row:
        row.body = body.body
    else:
        row = LaunchInstruction(agent_type=agent_type, body=body.body)
        db.add(row)
    db.commit()
    return {"agent_type": agent_type, "ok": True}


@app.post("/handoff/completion-log", response_model=CompletionLogOut)
def create_completion_log(body: CompletionLogCreate, db: Session = Depends(get_db)):
    log = CompletionLog(date=body.date, message=body.message)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ----- Deploy workflow to target repo (via GitHub API) -----

_WORKFLOW_TEMPLATE_PATH = Path(__file__).resolve().parent / "workflow-templates" / "handoff-status.yml"


class DeployWorkflowBody(BaseModel):
    owner: str
    repo: str
    github_token: str


@app.post("/handoff/deploy-workflow")
async def deploy_workflow_to_repo(body: DeployWorkflowBody):
    """
    通过 GitHub API 将 handoff-status workflow 写入指定仓库的 .github/workflows/handoff-status.yml。
    调用方需提供有 repo 写权限的 GitHub token；目标仓库需在 Settings → Actions 中配置 HANDOFF_API_URL。
    """
    path = ".github/workflows/handoff-status.yml"
    url_get = f"https://api.github.com/repos/{body.owner}/{body.repo}/contents/{path}"
    url_put = url_get
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {body.github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if not _WORKFLOW_TEMPLATE_PATH.is_file():
        raise HTTPException(status_code=500, detail="workflow template file not found")
    yaml_content = _WORKFLOW_TEMPLATE_PATH.read_text(encoding="utf-8")
    content_b64 = base64.b64encode(yaml_content.encode("utf-8")).decode("ascii")
    payload = {"message": "Add or update handoff-status workflow", "content": content_b64}

    async with httpx.AsyncClient() as client:
        get_r = await client.get(url_get, headers=headers)
        if get_r.status_code == 200:
            data = get_r.json()
            payload["sha"] = data.get("sha")
        elif get_r.status_code != 404:
            raise HTTPException(
                status_code=502,
                detail=f"github_api_error: {get_r.status_code} {get_r.text[:200]}",
            )
        put_r = await client.put(url_put, headers=headers, json=payload)
        if put_r.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"github_api_error: {put_r.status_code} {put_r.text[:200]}",
            )
    return {
        "ok": True,
        "repo": f"{body.owner}/{body.repo}",
        "path": path,
        "message": "Workflow 已写入目标仓库；请在该仓库 Settings → Secrets 中配置 HANDOFF_API_URL",
    }


# ----- GitHub Webhook (H-4) -----

PHASE_ID_PATTERN = re.compile(r"\[(?:Phase\s+)?([A-Z]+-\d+)\]", re.IGNORECASE)


def parse_phase_id_from_text(text: str | None) -> str | None:
    """Extract first [Phase X-Y] or [X-Y] from text."""
    if not text:
        return None
    m = PHASE_ID_PATTERN.search(text)
    return m.group(1).upper() if m else None


@app.post("/handoff/webhooks/github")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    db: Session = Depends(get_db),
):
    """Handle GitHub webhook: pull_request opened/synchronize -> 待审核 + pr_url; closed+merged -> 已完成."""
    if x_github_event != "pull_request":
        return {"ok": True, "ignored": "event is not pull_request"}
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    action = body.get("action")
    pr = body.get("pull_request") or {}
    title = pr.get("title") or ""
    html_url = pr.get("html_url") or ""
    merged = pr.get("merged") is True

    phase_id = parse_phase_id_from_text(title)
    if not phase_id:
        return {"ok": True, "skipped": "no [Phase X-Y] in PR title"}

    phase = db.query(Phase).filter(Phase.phase_id == phase_id).first()
    if not phase:
        return {"ok": True, "skipped": f"phase {phase_id} not in DB"}

    if action in ("opened", "reopened", "synchronize"):
        phase.status = "待审核"
        phase.pr_url = html_url
        phase.note = phase.note or ""  # keep existing note
        db.commit()
        return {"ok": True, "phase_id": phase_id, "status": "待审核", "pr_url": html_url}
    if action == "closed" and merged:
        phase.status = "已完成"
        phase.pr_url = html_url
        db.commit()
        return {"ok": True, "phase_id": phase_id, "status": "已完成"}
    return {"ok": True, "phase_id": phase_id, "action": action}
