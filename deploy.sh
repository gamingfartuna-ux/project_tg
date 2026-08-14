#!/usr/bin/env bash
set -e

# ==============================================================================
# deploy.sh — деплой на Debian: git pull + рестарт сервисов
# ==============================================================================

DEPLOY_USER="root"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/3] Установка зависимостей (если появились новые)..."
.venv/bin/pip install -e . -q

echo "[2/3] Рестарт сервисов..."
pkill -f "python api.py" 2>/dev/null || true
pkill -f "python bot.py" 2>/dev/null || true
sleep 1

echo "[3/3] Старт сервисов..."
.venv/bin/python api.py &
sleep 2
sleep 2
echo ""
echo "Готово!"
echo "  API : http://localhost:8080"
echo "  Bot : работает в фоне"
.venv/bin/python bot.py

