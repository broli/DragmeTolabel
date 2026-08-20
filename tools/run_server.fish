#!/usr/bin/env fish

# Determine project root relative to this script
set -l script_dir (status dirname)
set -l project_root (realpath "$script_dir/..")

cd "$project_root"

# Ensure root is in PYTHONPATH
set -gx PYTHONPATH "$project_root"

echo "Starting DragmeTolabel server from $project_root..."

# Execute uvicorn using project virtualenv or available python
if test -f "$project_root/.venv/bin/python"
    exec "$project_root/.venv/bin/python" -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 $argv
else if command -v uv >/dev/null 2>&1
    exec uv run python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 $argv
else
    exec python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 $argv
end
