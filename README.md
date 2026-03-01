# HANDOFF API

API + SQLite (or Postgres) for HANDOFF state. Used by 功能迭代 Agent to publish tasks and by backend/iOS Agents to read context. Optional: GitHub webhook for PR-driven status, single-page dashboard.

## Setup

```bash
cd handoff-api
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload
```

- Health: http://127.0.0.1:8000/health
- Full handoff: http://127.0.0.1:8000/handoff
- Dashboard: http://127.0.0.1:8000/dashboard
- Export markdown: http://127.0.0.1:8000/handoff/export?format=markdown
- GitHub webhook: `POST /handoff/webhooks/github` (set in GitHub repo Webhooks; PR title with `[Phase D-1]` drives status)

## GitHub Actions（部署到需要同步状态的仓库）

不接 Webhook 时，可用 GitHub Actions 在 PR 打开/合并时调 API 更新 Phase 状态。

**通过 API 一键写入目标仓库**：调用 `POST /handoff/deploy-workflow`，传入 `owner`、`repo`、`github_token`（对目标仓库有写权限的 token），即可将 `handoff-status.yml` 写入该仓库的 `.github/workflows/`，无需手动复制文件。前端/后端等目标 repo 各调一次即可。

```json
POST /handoff/deploy-workflow
{ "owner": "你的用户名", "repo": "learning-plan-api", "github_token": "ghp_xxx" }
```

写入后，在目标仓库 **Settings → Secrets and variables → Actions** 中配置 **`HANDOFF_API_URL`**（已部署的 API 根地址）即可生效。PR 标题需包含 `[Phase X-Y]` 或 `[D-1]`。

## 部署到服务器（本仓库）

push `main` 时自动部署：`.github/workflows/deploy.yml` 会将代码 SCP 到服务器 `~/deploy/handoff-api`，安装依赖、执行 seed、重启 uvicorn（端口 8000）。

**仓库 Secrets**（Settings → Secrets and variables → Actions）：

| Secret | 必填 | 说明 |
|--------|------|------|
| `SERVER_HOST` | 是 | 服务器 hostname 或 IP |
| `SERVER_USER` | 是 | SSH 登录用户名 |
| `SERVER_SSH_KEY` | 是 | 私钥全文（可写 deploy key） |
| `HANDOFF_DATABASE_URL` | 否 | 不设则用默认 SQLite |

部署后 API 监听 `0.0.0.0:8000`，可用 Nginx 反代并配 HTTPS。

## Database

- Default: SQLite at `./handoff.db`. Set `HANDOFF_DATABASE_URL` for Postgres.
- Tables: meta, phases, phase_tasks, current_tasks, launch_instructions, completion_log.

## API (summary)

- **Read**: `GET /handoff`, `GET /handoff/current-tasks`, `GET /handoff/phases`, `GET /handoff/completion-log`, `GET /handoff/launch-instructions`, `GET /handoff/export?format=markdown`
- **Write**: `PUT /handoff/meta/{key}`, `POST /handoff/phases`, `PATCH /handoff/phases/{id}`, `PATCH /handoff/phases/{id}/status`, `POST /handoff/phases/{id}/tasks`, `PATCH /handoff/phase-tasks/{id}`, `POST /handoff/current-tasks`, `PATCH /handoff/current-tasks/{id}`, `DELETE /handoff/current-tasks/{id}`, `PUT /handoff/launch-instructions/{agent_type}`, `POST /handoff/completion-log`

See OpenAPI at http://127.0.0.1:8000/docs when the server is running.
