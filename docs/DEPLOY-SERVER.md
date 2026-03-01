# handoff-api 部署与 Nginx（itsok 服务器）

## 1. GitHub 仓库 Secrets

在 **handoff-api** 仓库 → Settings → Secrets and variables → Actions 中配置：

| Secret | 说明 | 示例 |
|--------|------|------|
| `SERVER_HOST` | 服务器 IP 或 SSH 用的 hostname | `175.24.133.134` 或 `itsok` 对应主机 |
| `SERVER_USER` | SSH 登录用户 | `ubuntu` |
| `SERVER_SSH_KEY` | 私钥全文（用于 GitHub Actions 登录） | 粘贴 `id_rsa` 或 deploy key 内容 |
| `HANDOFF_DATABASE_URL` | 可选，Postgres 连接串 | `postgresql://user:pass@host/dbname` |

**生成并配置 SSH key（若尚未有）：**

- 本地或 CI 专用机：`ssh-keygen -t ed25519 -C "github-actions-handoff" -f handoff_deploy_key -N ""`
- 公钥 `handoff_deploy_key.pub` 内容追加到服务器 `~/.ssh/authorized_keys`
- 私钥 `handoff_deploy_key` 全文复制到 GitHub Secret `SERVER_SSH_KEY`

## 2. 服务器现状（itsok）

- **系统**：Ubuntu，Docker 已装；80/443 由容器 **my-ui**（itsok-web）占用。
- **Nginx**：运行在 my-ui 容器内，配置在镜像内（无挂载）。需通过 `docker cp` 注入 handoff 配置并 `nginx -s reload`。
- **handoff-api 部署目录**：`~/deploy/handoff-api`（push main 时由 workflow 上传并在此目录执行 uvicorn，监听 `0.0.0.0:8000`）。

## 3. Nginx 反代 handoff-api

handoff-api 跑在**宿主机** 8000 端口；my-ui 容器内通过宿主机网关 `172.17.0.1:8000` 访问。

**首次部署 handoff-api 后，在服务器执行：**

```bash
# 若未部署过，先 push main 触发 deploy，或手动把 deploy/nginx-handoff.conf 放到服务器
docker cp ~/deploy/handoff-api/deploy/nginx-handoff.conf my-ui:/etc/nginx/conf.d/
docker exec my-ui nginx -s reload
```

- 将域名 **handoff.itsokthen.com** 解析到本机公网 IP（如 `175.24.133.134`）。
- 若证书不是 `*.itsokthen.com`，需在 `deploy/nginx-handoff.conf` 中修改 `ssl_certificate` / `ssl_certificate_key` 路径后重新 `docker cp` 并 `nginx -s reload`。

完成后可通过 `https://handoff.itsokthen.com/health` 校验。
