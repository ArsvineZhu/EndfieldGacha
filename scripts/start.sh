#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR" || exit 1

PORT=5000
MODE="prod"
SYNC=1
RUNNER="auto"
CHECK_ONLY=0
UV_CMD=""
PY_CMD=""

print_banner() {
  echo
  echo "=========================================="
  echo "  Endfield Gacha Server Launcher (Shell)"
  echo "=========================================="
  echo
}

usage() {
  cat <<'EOF'
Usage: ./start.sh [options]

Options:
  --help, -h      Show help
  --dev           Dev mode (Flask debug, skip static compression)
  --port N        Set port (default: 5000)
  --no-sync       Skip uv dependency sync
  --uv            Force uv runner
  --python        Force python runner
  --check         Checks only, do not start server

Examples:
  ./start.sh
  ./start.sh --dev --port 5001
  ./start.sh --check
EOF
}

log() {
  printf '[%s] %s\n' "$1" "$2"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

pick_first_cmd() {
  local candidate
  for candidate in "$@"; do
    if has_cmd "$candidate"; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

is_port_in_use() {
  local port="$1"
  if has_cmd lsof; then
    lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  if has_cmd ss; then
    ss -ltn 2>/dev/null | grep -E "[\[\]:]$port[[:space:]]" >/dev/null 2>&1
    return $?
  fi
  if has_cmd netstat; then
    netstat -an 2>/dev/null | grep -E "[:.]$port[[:space:]].*LISTEN" >/dev/null 2>&1
    return $?
  fi
  return 1
}

find_free_port() {
  local start_port="$1"
  local max_delta="$2"
  local p
  for ((p = start_port; p <= start_port + max_delta; p++)); do
    if ! is_port_in_use "$p"; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

is_positive_integer() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

parse_args() {
  while (($# > 0)); do
    case "$1" in
      --help|-h)
        usage
        exit 0
        ;;
      --dev)
        MODE="dev"
        shift
        ;;
      --no-sync)
        SYNC=0
        shift
        ;;
      --check)
        CHECK_ONLY=1
        shift
        ;;
      --python)
        RUNNER="python"
        shift
        ;;
      --uv)
        RUNNER="uv"
        shift
        ;;
      --port)
        if (($# < 2)); then
          log "ERROR" "--port requires a value"
          usage
          exit 1
        fi
        PORT="$2"
        shift 2
        ;;
      *)
        log "ERROR" "Unknown argument: $1"
        usage
        exit 1
        ;;
    esac
  done
}

run_server() {
  local runner="$1"
  shift
  local args=("$@")
  if [[ "$runner" == "uv" ]]; then
    "$UV_CMD" run run.py server "${args[@]}"
  else
    "$PY_CMD" run.py server "${args[@]}"
  fi
}

main() {
  parse_args "$@"
  print_banner

  if [[ ! -f "run.py" ]]; then
    log "ERROR" "run.py not found. Run this script from project root."
    exit 1
  fi
  if [[ ! -f "pyproject.toml" ]]; then
    log "ERROR" "pyproject.toml not found. Project layout looks incomplete."
    exit 1
  fi

  local has_uv=0
  local has_py=0
  UV_CMD="$(pick_first_cmd uv uv.exe || true)"
  PY_CMD="$(pick_first_cmd python python3 python.exe || true)"
  [[ -n "$UV_CMD" ]] && has_uv=1
  [[ -n "$PY_CMD" ]] && has_py=1

  if [[ "$RUNNER" == "uv" && "$has_uv" -eq 0 ]]; then
    log "ERROR" "--uv is set, but uv command is not available."
    exit 1
  fi
  if [[ "$RUNNER" == "python" && "$has_py" -eq 0 ]]; then
    log "ERROR" "--python is set, but python command is not available."
    exit 1
  fi
  if [[ "$RUNNER" == "auto" ]]; then
    if [[ "$has_uv" -eq 1 ]]; then
      RUNNER="uv"
    elif [[ "$has_py" -eq 1 ]]; then
      RUNNER="python"
    else
      log "ERROR" "Neither uv nor python command is available."
      exit 1
    fi
  fi

  if ! is_positive_integer "$PORT"; then
    log "ERROR" "Port must be a positive integer. Current value: $PORT"
    exit 1
  fi

  if is_port_in_use "$PORT"; then
    log "WARN" "Port $PORT is in use. Trying to find a free port..."
    local free_port
    if ! free_port="$(find_free_port "$PORT" 20)"; then
      log "ERROR" "No free port found in range $PORT to $((PORT + 20)). Use --port."
      exit 1
    fi
    PORT="$free_port"
    log "INFO" "Switched to free port $PORT"
  fi

  if [[ "$RUNNER" == "uv" && "$SYNC" -eq 1 ]]; then
    log "STEP" "Syncing dependencies: uv sync --frozen"
    if ! "$UV_CMD" sync --frozen; then
      log "WARN" "uv sync --frozen failed. Trying uv sync..."
      if ! "$UV_CMD" sync; then
        log "ERROR" "Dependency sync failed. Check network and Python setup."
        exit 1
      fi
    fi
  fi

  if [[ "$RUNNER" == "python" ]]; then
    log "STEP" "Checking Python dependencies: flask and waitress..."
    if ! "$PY_CMD" -c "import flask, waitress" >/dev/null 2>&1; then
      log "ERROR" "Missing flask/waitress. Run: uv sync"
      exit 1
    fi
  fi

  local server_args=("--port" "$PORT")
  if [[ "$MODE" == "prod" ]]; then
    server_args=("--waitress" "--port" "$PORT")
  elif [[ "$MODE" == "dev" ]]; then
    server_args=("--dev" "--port" "$PORT")
  fi

  log "INFO" "Workdir: $ROOT_DIR"
  log "INFO" "Runner : $RUNNER"
  log "INFO" "Mode   : $MODE"
  log "INFO" "URL    : http://127.0.0.1:$PORT"
  echo

  if [[ "$CHECK_ONLY" -eq 1 ]]; then
    log "OK" "Checks passed for --check. Server was not started."
    exit 0
  fi

  log "STEP" "Starting server. Press Ctrl+C to stop."
  if [[ "$RUNNER" == "uv" ]]; then
    run_server "uv" "${server_args[@]}"
    local uv_exit=$?
    if [[ "$uv_exit" -ne 0 ]]; then
      if [[ "$has_py" -eq 1 ]]; then
        log "WARN" "uv launch failed. Trying python directly..."
        run_server "python" "${server_args[@]}"
        local py_exit=$?
        if [[ "$py_exit" -ne 0 ]]; then
          log "ERROR" "Server exited with code: $py_exit"
          exit "$py_exit"
        fi
      else
        log "ERROR" "Server exited with code: $uv_exit"
        exit "$uv_exit"
      fi
    fi
  else
    run_server "python" "${server_args[@]}"
    local py_exit=$?
    if [[ "$py_exit" -ne 0 ]]; then
      log "ERROR" "Server exited with code: $py_exit"
      exit "$py_exit"
    fi
  fi

  log "OK" "Server exited."
}

main "$@"
