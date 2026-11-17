#!/bin/sh
set -eu

VENV=/opt/venv

# venv лежит вне bind-mount /app, поэтому не перекрывается исходниками.
# sync идемпотентен: если зависимости уже стоят, это занимает доли секунды,
# зато после правок pyproject.toml / uv.lock окружение обновится само.
echo "Syncing Python dependencies..."
uv sync --frozen --no-dev --no-install-project

"$VENV/bin/python" manage.py migrate --noinput
exec "$VENV/bin/python" manage.py runserver 0.0.0.0:8000
