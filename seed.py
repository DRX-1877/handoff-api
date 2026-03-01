"""Seed database from current HANDOFF content. Run after tables are created."""
import os
import sys

# Allow running from project root or handoff-api/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import Base, Meta, Phase, PhaseTask, CurrentTask, LaunchInstruction, CompletionLog


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Meta: vision and static sections
    meta_entries = [
        ("vision_quote", "这个 app 可以叫今天学什么 一方面为已经知道想学什么的人规划学习路径 一方面也可以为迷茫的人 推荐可以学习的东西 主打一个学习的东西能有产出 当有人问提你今天做了什么的时候 能甩出一个报告 告诉他们 你没有虚度光影；然后我要在这个app里面的证明我的ai agent编程能力 然后要有设计感 要能分享"),
        ("vision_summary", "1. 学习必须导向产出，拒绝虚假努力。\n2. App 本身就是 AI Agent 编程能力的硬核名片。\n3. 极具设计感的成就报告，一键分享证明自己。"),
        ("design_refs", "docs/plans/2026-02-26-ai-agent-learning-app-vision.md, docs/plans/, docs/plans/2025-02-26-learning-plan-app-implementation.md, docs/plans/2025-02-26-learning-plan-app-design.md, docs/plans/2025-02-26-agent-teams-config.md, docs/learning-plan-app-description-for-ui.md"),
    ]
    for key, value in meta_entries:
        if db.query(Meta).filter(Meta.key == key).first() is None:
            db.add(Meta(key=key, value=value))

    # Phases (D-1, D-2, E-1, E-2) - completed in current HANDOFF
    phases_data = [
        ("D-1", "后端 — 报告生成 API + Agent", "已完成", None, None, "后端 Agent"),
        ("D-2", "iOS — 成就报告 UI + 分享", "已完成", None, None, "iOS Agent"),
        ("E-1", "后端 — 导师问答 API + Agent", "已完成", None, None, "后端 Agent"),
        ("E-2", "iOS — 导师问答 UI", "已完成", None, None, "iOS Agent"),
    ]
    for phase_id, title, status, pr_url, note, assignee in phases_data:
        if db.query(Phase).filter(Phase.phase_id == phase_id).first() is None:
            p = Phase(phase_id=phase_id, title=title, status=status, pr_url=pr_url, note=note, assignee=assignee)
            db.add(p)
    db.flush()  # get phase IDs

    # Phase tasks (checklists)
    phase_tasks_data = [
        ("D-1", [
            ("新建 reporter.py，实现 /report/plan/{plan_id} 的 GET（按 plan_id 拉取学习计划并生成报告 JSON）", True),
            ("报告 JSON 含：学习计划摘要、按日的学习记录、成就总结（可含 AI 生成短句）", True),
            ("在 openapi 中暴露接口，并写清请求/响应示例", True),
        ]),
        ("D-2", [
            ("新建成就报告页：展示报告内容（标题、日期、学习记录、成就总结）", True),
            ("支持分享为图片或 PDF（可先图片）", True),
            ("报告样式与 app 风格一致，可读性好", True),
        ]),
        ("E-1", [
            ("新建 mentor.py，实现导师验收问答 API（例如 POST /mentor/chat 或 /mentor/ask）", True),
            ("请求体含 plan_id（可选）与用户问题；响应为流式或非流式文本", True),
            ("在 openapi 中暴露接口", True),
        ]),
        ("E-2", [
            ("新建导师问答 UI：输入问题、展示回答（流式或一次性）", True),
            ("与学习计划/报告入口整合（例如从报告页或计划详情进入）", True),
        ]),
    ]
    for phase_id, tasks in phase_tasks_data:
        phase = db.query(Phase).filter(Phase.phase_id == phase_id).first()
        if phase and db.query(PhaseTask).filter(PhaseTask.phase_id == phase.id).count() == 0:
            for content, done in tasks:
                db.add(PhaseTask(phase_id=phase.id, content=content, done=done))

    # Current tasks (one row: no next task yet)
    if db.query(CurrentTask).count() == 0:
        db.add(CurrentTask(assignee="—", task_desc="Phase D、E 已完成；待功能迭代 Agent 分配下一轮任务", launch_cmd="", sort_order=0))

    # Launch instructions
    backend_instruction = """@docs/HANDOFF.md @learning-plan-api

你是后端 Agent。请先阅读 docs/HANDOFF.md。
当前 Phase D、E 已完成。根据「当前待办」或功能迭代 Agent 分配执行新任务。
完工后必须：执行 ./scripts/run_tests.sh backend，全部通过后更新 HANDOFF（打勾、补充状态、更新日志）
工作目录：learning-plan-api/"""

    ios_instruction = """@docs/HANDOFF.md @LearningPlanApp

你是 iOS Agent。请先阅读 docs/HANDOFF.md。
当前 Phase D、E 已完成。根据「当前待办」或功能迭代 Agent 分配执行新任务。
完工后必须：执行 ./scripts/run_tests.sh ios，全部通过后更新 HANDOFF（打勾、补充状态、更新日志）
工作目录：LearningPlanApp/"""

    for agent_type, body in [("backend", backend_instruction), ("ios", ios_instruction)]:
        if db.query(LaunchInstruction).filter(LaunchInstruction.agent_type == agent_type).first() is None:
            db.add(LaunchInstruction(agent_type=agent_type, body=body))

    # Completion log (recent entries)
    log_entries = [
        ("2026-03-01", "Phase D、E 全部完成：成就报告、导师验收；当前待办置空"),
        ("2026-02-27", "新增完工流程；后端部署上线"),
        ("2026-02-26", "Phase F UX 改版完成；产品愿景升级"),
    ]
    for date, message in log_entries:
        if db.query(CompletionLog).filter(CompletionLog.date == date, CompletionLog.message == message).first() is None:
            db.add(CompletionLog(date=date, message=message))

    db.commit()
    db.close()
    print("Seed done.")


if __name__ == "__main__":
    seed()
