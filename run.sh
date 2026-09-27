#!/usr/bin/env bash
# One-command runner for Gridlock.
#
#   ./run.sh app        Next.js + Supabase dashboard on http://localhost:3000 (default)
#   ./run.sh web        static Leaflet demo on http://localhost:8000
#   ./run.sh pipeline   only (re)build the dataset JSON, then exit
#
# Options:
#   --rebuild    re-run the Python pipeline even if its output already exists
#   --no-seed    (app mode) skip seeding Supabase
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
DATA_CLEAN="$ROOT/backend/data_clean"
OUTPUTS=("gridlock_dataset.json" "cost_impact_estimate.json")

MODE="app"
REBUILD=0
SEED=1
for arg in "$@"; do
  case "$arg" in
    app|web|pipeline) MODE="$arg" ;;
    --rebuild) REBUILD=1 ;;
    --no-seed) SEED=0 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown argument: $arg (try --help)" >&2; exit 1 ;;
  esac
done

step() { printf '\n==> %s\n' "$*"; }
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

setup_python() {
  command -v python3 >/dev/null || die "python3 not found"
  if [ ! -x "$VENV/bin/python" ]; then
    step "Creating virtualenv at .venv"
    python3 -m venv "$VENV"
  fi
  # Only reinstall when requirements.txt is newer than the last install.
  local stamp="$VENV/.requirements-installed"
  if [ ! -f "$stamp" ] || [ "$ROOT/backend/requirements.txt" -nt "$stamp" ]; then
    step "Installing Python dependencies"
    "$VENV/bin/python" -m pip install -q -r "$ROOT/backend/requirements.txt"
    touch "$stamp"
  fi
}

outputs_exist() {
  for f in "${OUTPUTS[@]}"; do [ -f "$DATA_CLEAN/$f" ] || return 1; done
}

run_pipeline() {
  if [ "$REBUILD" -eq 0 ] && outputs_exist; then
    step "Pipeline output already exists (use --rebuild to regenerate)"
    return
  fi
  setup_python
  step "Running data pipeline"
  (
    cd "$ROOT/backend/pipeline"
    for script in parse_desc_pdf.py parse_gpc_irp.py build_dataset.py cost_impact.py; do
      echo "  -> $script"
      "$VENV/bin/python" "$script"
    done
  )
}

run_web() {
  step "Copying dataset into web/data"
  mkdir -p "$ROOT/web/data"
  for f in "${OUTPUTS[@]}"; do cp "$DATA_CLEAN/$f" "$ROOT/web/data/"; done
  step "Serving static demo at http://localhost:8000 (Ctrl+C to stop)"
  cd "$ROOT/web"
  exec python3 -m http.server 8000
}

run_app() {
  command -v npm >/dev/null || die "npm not found (install Node.js 20+)"
  cd "$ROOT/frontend"
  [ -f .env.local ] || die "frontend/.env.local is missing. Run: cp frontend/.env.example frontend/.env.local, then fill in the Supabase keys (see frontend/README.md)"
  if [ ! -d node_modules ] || [ package-lock.json -nt node_modules ]; then
    step "Installing frontend dependencies"
    npm install
  fi
  if [ "$SEED" -eq 1 ]; then
    step "Seeding Supabase"
    node --env-file=.env.local scripts/seed.mjs
  fi
  step "Starting Next.js dev server at http://localhost:3000 (Ctrl+C to stop)"
  exec npm run dev
}

run_pipeline
case "$MODE" in
  pipeline) step "Done. Output is in backend/data_clean/" ;;
  web) run_web ;;
  app) run_app ;;
esac
