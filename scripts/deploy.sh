#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/emit/app"
BRANCH="main"
COMPOSE_FILE="docker-compose.prod.yml"
SERVICE="web"

echo "======================================"
echo " Deploying EMIT"
echo " Branch: ${BRANCH}"
echo " Dir: ${APP_DIR}"
echo " Time: $(date)"
echo "======================================"

cd "${APP_DIR}"

echo "==> Fetching latest code"
git fetch --all --prune
git reset --hard "origin/${BRANCH}"

echo "==> Building & restarting container"
sudo docker compose -f "${COMPOSE_FILE}" up -d --build

echo "==> Container status"
sudo docker compose -f "${COMPOSE_FILE}" ps

echo "==> Local health check"
if curl -fsS http://127.0.0.1:8000/docs >/dev/null; then
  echo "OK: app reachable on /docs"
else
  echo "WARNING: app not reachable on /docs"
fi

echo "==> Last logs"
sudo docker compose -f "${COMPOSE_FILE}" logs --tail=40 "${SERVICE}"

echo "==> Deploy finished"
