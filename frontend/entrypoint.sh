#!/bin/sh
set -eu

# node_modules живёт в named volume. Если package-lock.json новее установленных
# зависимостей (например, после добавления пакета), переустанавливаем их.
if [ ! -d node_modules ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then
    echo "Dependencies changed, running npm ci..."
    npm ci --no-audit --no-fund
fi

exec npm run dev -- --host 0.0.0.0 --port 5173
