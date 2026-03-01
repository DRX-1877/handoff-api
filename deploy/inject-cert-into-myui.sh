#!/bin/bash
# 将宿主机上的 handoff 证书复制进 my-ui 并重载 nginx。证书可由 certbot 或 acme.sh 签发，见 docs/SSL-CERT-HANDOFF.md
# 用法：
#   ./inject-cert-into-myui.sh /etc/letsencrypt/live/handoff.itsokthen.com   # certbot 路径
#   ./inject-cert-into-myui.sh ~/.acme.sh/handoff.itsokthen.com               # acme.sh 路径
set -e
CERT_DIR="${1:-}"
CONTAINER="${2:-my-ui}"

if [ -z "$CERT_DIR" ]; then
  echo "Usage: $0 <path-to-cert-dir> [container_name]"
  echo "  e.g. $0 /etc/letsencrypt/live/handoff.itsokthen.com"
  echo "  e.g. $0 ~/.acme.sh/handoff.itsokthen.com"
  exit 1
fi
if [ ! -d "$CERT_DIR" ] && [ ! -L "$CERT_DIR" ]; then
  echo "Not a directory: $CERT_DIR"
  exit 1
fi
CERT_DIR="$(cd "$CERT_DIR" 2>/dev/null && pwd)"
[ -z "$CERT_DIR" ] && echo "Cannot cd to $1" && exit 1

# 兼容 certbot (fullchain.pem + privkey.pem) 与 acme.sh (fullchain.cer + domain.key)
if [ -f "$CERT_DIR/fullchain.pem" ]; then
  FULLCHAIN="$CERT_DIR/fullchain.pem"
  PRIVKEY="$CERT_DIR/privkey.pem"
elif [ -f "$CERT_DIR/fullchain.cer" ]; then
  FULLCHAIN="$CERT_DIR/fullchain.cer"
  PRIVKEY="$CERT_DIR/handoff.itsokthen.com.key"
  [ ! -f "$PRIVKEY" ] && PRIVKEY="$CERT_DIR/privkey.pem"
else
  echo "No fullchain.pem or fullchain.cer in $CERT_DIR"
  exit 1
fi
[ ! -f "$PRIVKEY" ] && echo "Private key not found" && exit 1

# certbot 的 live 目录是符号链接，docker cp 会复制链接导致容器内失效；用临时文件复制实体
TMPDIR=""
if [ -L "$FULLCHAIN" ] || [ -L "$PRIVKEY" ]; then
  TMPDIR="$(mktemp -d)"
  cp -L "$FULLCHAIN" "$TMPDIR/handoff-fullchain.pem"
  cp -L "$PRIVKEY" "$TMPDIR/handoff-privkey.pem"
  FULLCHAIN="$TMPDIR/handoff-fullchain.pem"
  PRIVKEY="$TMPDIR/handoff-privkey.pem"
fi
[ -n "$TMPDIR" ] && trap "rm -rf $TMPDIR" EXIT

docker exec "$CONTAINER" mkdir -p /etc/nginx/certs
docker cp "$FULLCHAIN" "$CONTAINER:/etc/nginx/certs/handoff-fullchain.pem"
docker cp "$PRIVKEY" "$CONTAINER:/etc/nginx/certs/handoff-privkey.pem"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
docker cp "$SCRIPT_DIR/nginx-handoff.conf" "$CONTAINER:/etc/nginx/conf.d/"
docker exec "$CONTAINER" nginx -s reload
echo "Cert injected and nginx reloaded."
