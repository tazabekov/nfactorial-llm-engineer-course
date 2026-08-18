#!/usr/bin/env bash
# Собирает архив для сдачи: только код, без окружения, ключей и тяжёлых файлов.
set -euo pipefail

NAME="${1:?Использование: make_zip.sh Имя_Фамилия}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAGING="$(mktemp -d)/${NAME}"

mkdir -p "${STAGING}"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' \
      --exclude 'cache' --exclude 'output' --exclude 'assets-private' \
      --exclude '.env' --exclude '*.pt' --exclude '*.bin' --exclude '*.ckpt' \
      "${PROJECT_DIR}/" "${STAGING}/"

cd "$(dirname "${STAGING}")"
zip -rq "${PROJECT_DIR}/${NAME}.zip" "${NAME}"
echo "Готово: ${PROJECT_DIR}/${NAME}.zip"
unzip -l "${PROJECT_DIR}/${NAME}.zip" | tail -5
