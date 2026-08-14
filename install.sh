#!/usr/bin/env bash
set -e

# ==============================================================================
# install.sh — установка всех зависимостей на чистый Debian/Ubuntu
# ==============================================================================

DEBIAN_FRONTEND=noninteractive

echo "[1/4] Обновление apt..."
apt-get update -qq

echo "[2/4] Установка системных пакетов..."
apt-get install -y -qq python3 python3-venv python3-pip git curl

echo "[3/4] Создание виртуального окружения..."
python3 -m venv .venv

echo "[4/4] Установка Python-зависимостей..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -e . -q

echo ""
echo "Готово!"
echo ""
echo "Следующий шаг — заполните .env:"
echo "  cp .env.example .env"
echo "  nano .env"
echo ""
echo "Запуск:"
echo "  ./run.sh"
