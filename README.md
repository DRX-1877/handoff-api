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

## Database

- Default: SQLite at `./handoff.db`. Set `HANDOFF_DATABASE_URL` for Postgres.
- Tables: meta, phases, phase_tasks, current_tasks, launch_instructions, completion_log.

## API (summary)

- **Read**: `GET /handoff`, `GET /handoff/current-tasks`, `GET /handoff/phases`, `GET /handoff/completion-log`, `GET /handoff/launch-instructions`, `GET /handoff/export?format=markdown`
- **Write**: `PUT /handoff/meta/{key}`, `POST /handoff/phases`, `PATCH /handoff/phases/{id}`, `PATCH /handoff/phases/{id}/status`, `POST /handoff/phases/{id}/tasks`, `PATCH /handoff/phase-tasks/{id}`, `POST /handoff/current-tasks`, `PATCH /handoff/current-tasks/{id}`, `DELETE /handoff/current-tasks/{id}`, `PUT /handoff/launch-instructions/{agent_type}`, `POST /handoff/completion-log`

See OpenAPI at http://127.0.0.1:8000/docs when the server is running.
