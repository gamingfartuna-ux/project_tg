#!/usr/bin/env bash
set -e

# ==============================================================================
# deploy.sh — деплой на Debian: git pull + рестарт сервисов
# ==============================================================================

DEPLOY_USER="root"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/4] Переход в директорию проекта..."
cd "$APP_DIR"

echo "[2/4] Git pull..."
git pull origin master

echo "[3/4] Установка зависимостей (если появились новые)..."
.venv/bin/pip install -e . -q

echo "[4/4] Рестарт сервисов..."
pkill -f "python api.py" 2>/dev/null || true
pkill -f "python bot.py" 2>/dev/null || true
sleep 1

.venv/bin/python api.py &
sleep 2
.venv/bin/python bot.py &

sleep 2
echo ""
echo "Готово!"
echo "  API : http://localhost:8080"
echo "  Bot : работает в фоне"
