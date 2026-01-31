#!/bin/sh
set -e

log() {
  printf '%s | %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2
}

# Unraid-style PUID / PGID
PUID="${PUID:-0}"
PGID="${PGID:-0}"

# Ensure directories exist (Unraid maps these)
: "${TASKS_DIR:=/tasks}"
: "${CONFIG_DIR:=/config}"
: "${DOWNLOADS_DIR:=/downloads}"

# Validate directories are accessible
for dir in "$TASKS_DIR" "$CONFIG_DIR" "$DOWNLOADS_DIR"; do
  mkdir -p "$dir" || { log "ERROR: Failed to create directory: $dir"; exit 1; }
  if [ ! -w "$dir" ]; then
    log "ERROR: Directory is not writable: $dir"
    exit 1
  fi
done

log "Configuration validated:"
log "  TASKS_DIR: $TASKS_DIR"
log "  CONFIG_DIR: $CONFIG_DIR"
log "  DOWNLOADS_DIR: $DOWNLOADS_DIR"

log "Updating gallery-dl to latest..."
pip install --no-cache-dir --upgrade gallery-dl


# remove stale task lock files from previous container run
# Only remove lock files in task directories: $TASKS_DIR/<slug>/lock
find "$TASKS_DIR" -mindepth 2 -maxdepth 2 -type f -name "lock" -print -delete || true


# Decide how we run things: as root or as numeric uid:gid
if [ "$PUID" != "0" ] && [ "$PGID" != "0" ]; then
  APP_USER_SPEC="$PUID:$PGID"
  log "Using PUID=$PUID PGID=$PGID for ownership and processes"

  # Own the mapped directories (best effort)
  chown -R "$PUID:$PGID" "$TASKS_DIR" "$CONFIG_DIR" "$DOWNLOADS_DIR" 2>/dev/null || true
else
  APP_USER_SPEC="root"
  log "PUID/PGID not set (or zero), running as root."
fi

# Setup cron to run scheduler as the chosen user
log "Setting up cron entry for scheduler..."
CRON_LINE="* * * * * /usr/local/bin/gosu $APP_USER_SPEC /usr/local/bin/python /app/scheduler.py >> /var/log/cron.log 2>&1"

echo "$CRON_LINE" | crontab -

log "Starting cron..."
touch /var/log/cron.log
CRON_STARTUP_RETRIES=5
CRON_STARTED=0
# Run cron in foreground mode but background the process so the app can start.
cron -f &
CRON_PID=$!
for attempt in $(seq 1 "$CRON_STARTUP_RETRIES"); do
  if kill -0 "$CRON_PID" 2>/dev/null; then
    CRON_STARTED=1
    break
  fi
  sleep 1
done
if [ "$CRON_STARTED" -eq 0 ]; then
  log "ERROR: Cron failed to start. Check /var/log/cron.log or system logs for details."
  exit 1
fi

log "Starting web app as $APP_USER_SPEC..."
# Exec gunicorn as the chosen user so it writes files with correct ownership
exec gosu "$APP_USER_SPEC" "$@"
