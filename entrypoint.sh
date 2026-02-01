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
# Export environment variables so cron job can access them
export TASKS_DIR CONFIG_DIR DOWNLOADS_DIR TZ
CRON_LINE="* * * * * /usr/local/bin/gosu $APP_USER_SPEC bash -c 'export TASKS_DIR=$TASKS_DIR CONFIG_DIR=$CONFIG_DIR DOWNLOADS_DIR=$DOWNLOADS_DIR TZ=$TZ && /usr/local/bin/python /app/scheduler.py' 2>&1 | tee -a /var/log/artillery_scheduler.log"

echo "$CRON_LINE" | crontab -

log "Starting cron..."
touch /var/log/cron.log
touch /var/log/artillery_scheduler.log
chmod 666 /var/log/artillery_scheduler.log /var/log/cron.log
cron

log "Starting web app as $APP_USER_SPEC..."
# Exec gunicorn as the chosen user so it writes files with correct ownership
exec gosu "$APP_USER_SPEC" "$@"
