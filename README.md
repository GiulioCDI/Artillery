# Artillery

Artillery is a simple web UI for [`gallery-dl`](https://github.com/mikf/gallery-dl).

It lets you:

* Create repeatable download tasks
* Schedule them with cron
* Run them on demand
* Keep everything isolated per-task
* Browse your latest downloads via an animated media wall

All wrapped in a dark, minimal interface designed to live inside Docker/Unraid.

---

## Features

* Task management

  * Create/edit named tasks
  * Each task has:

    * URL list (`urls.txt`)
    * Custom `gallery-dl` command
    * Optional cron schedule
    * Per-task logs (`logs.txt`)
* Per-task isolation

  * Each task gets its own folder under `/tasks/<task-slug>`
  * Stores name, URLs, cron, command, logs, last run, archive, pause/lock state, etc.
* Global gallery-dl config

  * Single `gallery-dl.conf` shared across all tasks
  * Editable from the UI
  * Button to “Load default from GitHub”
* Scheduling

  * Cron-based scheduler runs every minute inside the container
  * Cron expressions per task (`* * * * *`, `*/5 * * * *`, etc.)
  * Real-time cron expression validation with visual feedback (green = valid, red = invalid)
  * Displays next run time when hovering over cron expression
  * Tasks can be:

    * Run manually
    * Paused/unpaused (paused tasks won't auto-run via cron, but can still be manually triggered)
    * Run automatically by cron on schedule
    * Status updates live without refresh
* Logging

  * Each run creates a timestamped log file at `/tasks/<slug>/logs/run_YYYYMMDD_HHMMSS.log`
  * Main `logs.txt` accumulates all runs after completion
  * ANSI escape sequences stripped for clean display in UI (only color formatting retained)
  * Real-time log viewer with auto-scroll, level-based coloring, and manual pause support
  * Inline error panel with the most recent error lines
  * Includes command line + exit code info
  * All logs visible in Docker container logs (Unraid UI) for easy debugging
  * Scheduler logs every task execution and errors to both file and container output
* Media wall dashboard

  * Home page shows a 3-row animated wall of recent downloads from `/downloads`
  * Rows scroll alternately left/right
  * Handles huge libraries by only scanning the most recently active directories
* Docker/Unraid-friendly

  * Runs under `gunicorn`
  * Uses `PUID` / `PGID` for proper file ownership on the host
  * Uses `/config`, `/tasks`, `/downloads` as primary mount points
  * Uses the `gallery-dl` version pinned in `requirements.txt`
  * Container timezone support via `TZ` environment variable (e.g., `TZ=America/Toronto`)
  * All scheduler activity logged to Docker container logs for easy monitoring

---

## Interface

### Dashboard

* Welcome panel explaining how Artillery and gallery-dl fit together
* 3-row animated media wall:

  * Recent images (and basic video placeholders) from `/downloads`
  * Smooth scrolling rows, alternating direction per row

![Artillery Home](screenshots/home.png)

### Tasks

* Table of tasks showing:

  * Name
  * Status (idle / running / paused)
  * Cron expression
  * Last run time (shown in your browser's local timezone)
  * Actions (Run, Cancel, Pause/Unpause, Edit, Delete)
  * Live status updates without reloading the page
* Task editor:

  * Task name
  * URL list (one URL per line)
  * Cron schedule
  * Command builder for common flags (input file, archive, metadata, etc.)
  * Raw command text area for advanced users
* Output panel:

  * Live log tail and error highlights
  * Auto-refreshes while visible

![Artillery Tasks](screenshots/tasks.png)

### Config

* A simple editor for `gallery-dl.conf`
* Container time display with 12H/24H format toggle (shows current container timezone)
* Media wall controls:

  * Toggle media wall on/off (state persists across container restarts)
  * Refresh cache button to manually rebuild media index
  * Seed button to rebuild entire media index from scratch
* Buttons for gallery-dl config:

  * Save – write your changes
  * Load default from GitHub – fetches the example config from the official gallery-dl repo

![Artillery Config](screenshots/config.png)

---

## Example docker run

```bash
docker run -d \
  --name artillery \
  -p 8088:80 \
  -e TASKS_DIR=/tasks \
  -e CONFIG_DIR=/config \
  -e DOWNLOADS_DIR=/downloads \
  -e TZ=America/Toronto \
  -e PUID=99 \
  -e PGID=100 \
  -e ARTILLERY_AUTH_ENABLED=1 \
  -e ARTILLERY_USERNAME=admin \
  -e ARTILLERY_PASSWORD=your-password \
  -v /mnt/user/appdata/artillery/config:/config \
  -v /mnt/user/appdata/artillery/tasks:/tasks \
  -v /mnt/user/pictures:/downloads \
  giuliocdi/artillery

### Environment Variables

**Core configuration:**
- `TASKS_DIR` – path to task folders (default: `/tasks`)
- `CONFIG_DIR` – path to gallery-dl.conf and media wall cache (default: `/config`)
- `DOWNLOADS_DIR` – path to final gallery-dl output (default: `/downloads`)
- `TZ` – container timezone for cron scheduling (e.g., `America/Toronto`, `Europe/London`)
- `PUID` / `PGID` – numeric user/group IDs for file ownership (Unraid-style)

**Authentication:**
- `ARTILLERY_AUTH_ENABLED` – enable/disable login screen (default: `1`; accepts `1/0`, `true/false`, `yes/no`, `on/off`)
- `ARTILLERY_USERNAME` – login username (default: `admin`)
- `ARTILLERY_PASSWORD` – login password (default: `artillery`)

**Media wall:**
- `MEDIA_WALL_ENABLED` – enable/disable media wall dashboard (default: `1`; note: can be toggled in UI and state persists)
- `MEDIA_WALL_ITEMS` – items per row on dashboard (default: `45`; range: 1-500)
- `MEDIA_WALL_COPY_LIMIT` – max files to cache per task (default: `100`; range: 1-1000)
- `MEDIA_WALL_CACHE_VIDEOS` – cache video files in media wall (default: `0`; accepts `1/0`, `true/false`, `yes/no`, `on/off`)
- `MEDIA_WALL_MIN_REFRESH_SECONDS` – throttle media wall refresh interval (default: `300`)

**Logging:**
- `ARTILLERY_LOG_LEVEL` – logging verbosity (default: `INFO`; accepts `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)

### Authentication

Authentication is disabled by default. To enable:

* Set `ARTILLERY_AUTH_ENABLED=1`
* Set `ARTILLERY_USERNAME` and `ARTILLERY_PASSWORD` to your desired credentials (plaintext, no hashing required)
* Users will see a login page with animated background where they enter username and password
