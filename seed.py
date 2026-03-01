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

    # Meta: vision, design refs, and full HANDOFF sections
    meta_entries = [
        ("vision_quote", "这个 app 可以叫今天学什么 一方面为已经知道想学什么的人规划学习路径 一方面也可以为迷茫的人 推荐可以学习的东西 主打一个学习的东西能有产出 当有人问提你今天做了什么的时候 能甩出一个报告 告诉他们 你没有虚度光影；然后我要在这个app里面的证明我的ai agent编程能力 然后要有设计感 要能分享"),
        ("vision_summary", "1. 学习必须导向产出，拒绝虚假努力。\n2. App 本身就是 AI Agent 编程能力的硬核名片。\n3. 极具设计感的成就报告，一键分享证明自己。"),
        ("design_refs", "docs/plans/2026-02-26-ai-agent-learning-app-vision.md, docs/plans/, docs/plans/2025-02-26-learning-plan-app-implementation.md, docs/plans/2025-02-26-learning-plan-app-design.md, docs/plans/2025-02-26-agent-teams-config.md, docs/learning-plan-app-description-for-ui.md"),
        ("agent_roles", "| Agent | 职责 | 工作区 |\n|-------|------|--------|\n| **功能迭代 Agent** | 统筹迭代、拆任务、分配、验收、推动下一轮 | `docs/` |\n| **iOS Agent** | SwiftUI、SwiftData、前端交互与展示 | `LearningPlanApp/` |\n| **后端 Agent** | FastAPI、Agent 工作流、数据分析与生成 | `learning-plan-api/` |"),
        ("completion_workflow", "1. 运行测试脚本：./scripts/run_tests.sh（或分步后端 pytest、iOS xcodebuild test）。若失败则修复后重跑。\n2. 更新 HANDOFF：将对应任务 [ ] 改为 [x]；在「当前状态」中补充完成内容；在「更新日志」末尾新增一行。"),
        ("current_state", "iOS 已完成：数据模型 Plan/Phase/PlanItem/Task/ChecklistItem；视图 ContentView/ExploreView/OnboardingPromiseView/HomeView/PlanModeView/NewPlanView/PlanDetailView/PomodoroView/ReportView/VerifyChatView；服务 TemplateAPIService/PlanModeService/ReportService/VerifyService；Theme+HapticManager+L10n；已对接 GET /api/templates、POST /api/generate、POST /api/chat/guide、POST /api/generate_report、POST /api/chat/verify。\n后端已完成：FastAPI+CORS；API 同上+GET /health；模板引擎 TemplateBase+quant/ai_agent；agents planner/writer/reviewer/guide/reporter/interviewer；model_choice deepseek/doubao/zhipu；Phase A hours 支持；schemas/plan.py 与 iOS 对齐；已部署 42.193.176.27:8000。\n已决定放弃：极客控制台/双面板透明工作流。"),
        ("iteration_priority", "| 优先级 | Phase | 理由 |\n|--------|-------|------|\n| 1 | **D (报告引擎)** | 直接击中核心痛点，分享属性强，见效快 |\n| 2 | **E (导师问答)** | 交互体验升级，硬核证明 Agent 能力，依赖 D 的产出数据 |"),
        ("launch_cmd_help", "方式一（命令行）：安装 Cursor CLI 后，./scripts/run_agent.sh backend|ios|test|iteration。\n方式二（Composer）：项目根目录执行 ./scripts/agent_startup.sh backend（或 ios），将输出粘贴到 Composer；macOS 可用 | pbcopy 复制到剪贴板。"),
    ]
    for key, value in meta_entries:
        if db.query(Meta).filter(Meta.key == key).first() is None:
            db.add(Meta(key=key, value=value))

    # Phases: F (UX 改版), D-1, D-2, E-1, E-2
    phases_data = [
        ("F", "Phase F：UX 改版", "已完成", None, None, None),
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
        ("F", [
            ("ExploreView.swift 卡片墙（方向卡片 + 自由输入）", True),
            ("OnboardingPromiseView.swift 承诺屏（动画 + 对比 + CTA）", True),
            ("HomeView.swift 改版为数据仪表盘（热力图 + 统计 + 进度条）", True),
            ("ContentView.swift 路由分流（无计划→ExploreView，有计划→TabView）", True),
            ("PlanModeView.swift 支持 topic 预填参数", True),
        ]),
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

    # Completion log：与 HANDOFF.md 更新日志表一致（共 6 条，seed 时重置为此）
    log_entries = [
        ("2026-03-01", "Phase D、E 全部完成：成就报告（ReportView + ShareSheet）、导师验收（VerifyChatView + POST /api/chat/verify）；当前待办置空，待下一轮迭代"),
        ("2026-02-27", "新增「完工流程」：Agent 必须跑 ./scripts/run_tests.sh 通过后再更新 HANDOFF；Backend/iOS 启动指令已加入此要求"),
        ("2025-02-26", "初始创建，Phase A/B/C 待办"),
        ("2026-02-26", "产品愿景升级为「今天学什么」；新增 Phase D（报告引擎）、Phase E（导师问答）；放弃极客控制台方案；更新 Agent 启动指令"),
        ("2026-02-27", "后端已部署上线（http://42.193.176.27:8000）；Phase A 完成（custom intensity + hours 支持）；`/api/chat/guide` 联调验证通过（豆包）；CI/CD pipeline 搭建完成"),
        ("2026-02-26", "Phase F（UX 改版）完成：新增 ExploreView（卡片墙）、OnboardingPromiseView（承诺屏）；HomeView 改为仪表盘（热力图+统计）；ContentView 路由分流；PlanModeView 支持 topic 预填"),
    ]
    db.query(CompletionLog).delete()
    for date, message in log_entries:
        db.add(CompletionLog(date=date, message=message))

    db.commit()
    db.close()
    print("Seed done.")


if __name__ == "__main__":
    seed()
