# 为 handoff.itsokthen.com 申请 HTTPS 证书（Let's Encrypt）

子域名单独申请证书，用 Let's Encrypt 免费签发，再注入 my-ui 容器。

---

## 方式一：HTTP-01（certbot，无需 DNS API）

**前提**：能临时让 80 端口对 `handoff.itsokthen.com` 的 `/.well-known/acme-challenge/` 提供访问（由 my-ui 提供或临时停掉 my-ui 用 certbot standalone）。若 my-ui 已占 80，需在 my-ui 里加一个 webroot 并挂载宿主机目录。

### 1. 服务器上安装 certbot

```bash
sudo apt update && sudo apt install -y certbot
```

### 2. 在 my-ui 中提供 ACME 挑战目录（二选一）

**2a) 若可为 my-ui 增加挂载并重启**

- 宿主机建目录：`mkdir -p /home/ubuntu/acme-webroot`
- 重启 my-ui 时增加挂载：`-v /home/ubuntu/acme-webroot:/var/www/acme:ro`
- 在 handoff 的 nginx 配置里增加：

```nginx
location ^~ /.well-known/acme-challenge/ {
    root /var/www/acme;
    default_type text/plain;
}
```

然后执行：`docker cp ... nginx conf ...`、`docker exec my-ui nginx -s reload`。

**2b) 不重启 my-ui：用 standalone 临时占 80**

- 临时停掉 my-ui：`docker stop my-ui`
- 执行签发（见下），完成后再：`docker start my-ui`

### 3. 签发证书

```bash
# 2a 时用 webroot（目录需与上面一致）
sudo certbot certonly --webroot -w /home/ubuntu/acme-webroot -d handoff.itsokthen.com --non-interactive --agree-tos -m 你的邮箱

# 2b 时用 standalone（确保 80 未被占用）
sudo certbot certonly --standalone -d handoff.itsokthen.com --non-interactive --agree-tos -m 你的邮箱
```

证书会出现在：`/etc/letsencrypt/live/handoff.itsokthen.com/fullchain.pem` 和 `privkey.pem`。

### 4. 把证书注入 my-ui 并启用 HTTPS

在服务器上执行（或使用仓库里的脚本）：

```bash
sudo mkdir -p /tmp/nginx-certs
sudo cp /etc/letsencrypt/live/handoff.itsokthen.com/fullchain.pem /tmp/nginx-certs/
sudo cp /etc/letsencrypt/live/handoff.itsokthen.com/privkey.pem /tmp/nginx-certs/
sudo chown -R ubuntu:ubuntu /tmp/nginx-certs
docker cp /tmp/nginx-certs/fullchain.pem my-ui:/etc/nginx/certs/handoff-fullchain.pem
docker cp /tmp/nginx-certs/privkey.pem my-ui:/etc/nginx/certs/handoff-privkey.pem
```

然后更新 handoff 的 nginx 配置，把 `ssl_certificate` / `ssl_certificate_key` 改为容器内路径，例如：

- `ssl_certificate /etc/nginx/certs/handoff-fullchain.pem;`
- `ssl_certificate_key /etc/nginx/certs/handoff-privkey.pem;`

再 `docker cp` 新配置到 my-ui、`docker exec my-ui nginx -s reload`。

---

## 方式二：DNS-01（acme.sh，适合有 DNS API 时）

不需要开放 80，适合无法改 my-ui 或不想动 nginx 时。

### 1. 安装 acme.sh

```bash
curl https://get.acme.sh | sh -s email=你的邮箱
source ~/.bashrc  # 或重新登录
```

### 2. 按 DNS 厂商配置并签发

示例（Cloudflare）：

```bash
export CF_Token="你的_Cloudflare_API_Token"
export CF_Account_ID="你的_Account_ID"
acme.sh --issue --dns dns_cf -d handoff.itsokthen.com
```

证书会在 `~/.acme.sh/handoff.itsokthen.com/`（如 `fullchain.cer`、`handoff.itsokthen.com.key`）。

### 3. 把证书注入 my-ui

```bash
mkdir -p ~/nginx-certs
cp ~/.acme.sh/handoff.itsokthen.com/fullchain.cer ~/nginx-certs/handoff-fullchain.pem
cp ~/.acme.sh/handoff.itsokthen.com/handoff.itsokthen.com.key ~/nginx-certs/handoff-privkey.pem
docker exec my-ui mkdir -p /etc/nginx/certs
docker cp ~/nginx-certs/handoff-fullchain.pem my-ui:/etc/nginx/certs/
docker cp ~/nginx-certs/handoff-privkey.pem my-ui:/etc/nginx/certs/
```

然后更新 handoff 的 nginx 配置指向 `/etc/nginx/certs/handoff-fullchain.pem` 和 `handoff-privkey.pem`，再 `docker cp` 配置并 `nginx -s reload`。

---

## 续期

- **certbot**：`sudo certbot renew`（可加 cron：`0 3 * * * certbot renew --quiet`）。续期后需再次把新证书 cp 进 my-ui 并 reload nginx。
- **acme.sh**：自动续期；续期后同样需把新证书复制进 my-ui 并 reload。

建议写一个小脚本：从宿主机证书路径 copy 到容器并执行 `docker exec my-ui nginx -s reload`，在续期 cron 里调用。
