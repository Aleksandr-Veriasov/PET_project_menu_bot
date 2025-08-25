#!/usr/bin/env bash
set -Eeuo pipefail

# ── настройки по флагам ────────────────────────────────────────────────────────
WITH_VOLUMES=false
NO_CACHE=false
PRUNE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--volumes) WITH_VOLUMES=true; shift ;;
    -c|--no-cache) NO_CACHE=true; shift ;;
    -p|--prune) PRUNE=true; shift ;;
    -h|--help)
      cat <<'USAGE'
Usage: ./refresh.sh [options]

Options:
  -v, --volumes   also remove named volumes (DANGEROUS)
  -c, --no-cache  rebuild images with --no-cache
  -p, --prune     docker image/builder prune after down
  -h, --help      show this help
USAGE
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ── выбираем команду docker compose (v2 vs v1) ────────────────────────────────
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif docker-compose version >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "✗ Docker Compose не найден." >&2
  exit 1
fi

echo "▶ Using: $DC"

# ── спускаем проект ───────────────────────────────────────────────────────────
DOWN_ARGS=(down --remove-orphans --rmi local)
$WITH_VOLUMES && DOWN_ARGS+=(--volumes)

echo "🔻 Stopping & removing: ${DOWN_ARGS[*]}"
$DC "${DOWN_ARGS[@]}"

# ── чистим мусор (по желанию) ────────────────────────────────────────────────
if $PRUNE; then
  echo "🧹 docker image prune -f"
  docker image prune -f || true
  echo "🧹 docker builder prune -f"
  docker builder prune -f || true
fi

# ── билд ──────────────────────────────────────────────────────────────────────
BUILD_ARGS=(build --pull)
$NO_CACHE && BUILD_ARGS+=(--no-cache)
echo "🛠  Building: ${BUILD_ARGS[*]}"
$DC "${BUILD_ARGS[@]}"

# ── ап ───────────────────────────────────────────────────────────────────────
echo "🚀 Up: detached mode"
$DC up -d

echo "✅ Done."
