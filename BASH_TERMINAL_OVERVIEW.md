# 🚀 Bash Terminal Feature - Complete Overview

## What Was Built

A full-featured **Bash Terminal** interface for Artillery that provides:

1. **Live Command Execution**
   - Type bash commands and execute them instantly
   - Real-time output display
   - Exit code tracking
   - Error/warning highlighting

2. **Script Management**
   - Create and save bash scripts
   - Edit existing scripts
   - Run scripts with one click
   - Optional cron scheduling
   - Script metadata (description, schedule)

3. **File System Browser**
   - Navigate directories
   - View file details
   - Edit text files
   - Create/delete files
   - Create/delete directories

4. **Security & Control**
   - Disabled by default (opt-in)
   - Toggle enable/disable at runtime
   - Path traversal prevention
   - Sensitive directories blocked
   - Command timeout (30s default)
   - HTML output escaping
   - Full audit logging

## How to Use It

### 1. Enable the Feature

**Option A: Environment Variable**
```bash
export BASH_TERMINAL_ENABLED=1
python app.py
```

**Option B: Runtime Toggle** (no restart needed)
- Go to Config tab
- Scroll to "Bash Terminal (Advanced)"
- Click toggle button
- Terminal tab appears immediately

### 2. Open Terminal Tab

After enabling, a new "Terminal" tab appears in the navbar (between Tasks and Config).

Click it to open the terminal interface.

### 3. Execute Commands

In the terminal panel:
```bash
# Type command here
ls -la /home

# Press Enter or click Run
# Output appears below instantly
```

### 4. Create Scripts

Click "New Script" in the Saved Scripts panel:

```bash
#!/bin/bash
echo "Hello from Artillery"
date
ps aux | head -5
```

- Enter filename: `example.sh`
- Add description: "Example script"
- Optional: Set cron `0 2 * * *` (2 AM daily)
- Click "Save Script"

### 5. Run Scripts

Click "Run" next to any script in the list.

Output appears in the terminal panel.

### 6. Manage Files

Use the File Browser to:
- Navigate directories
- View file details
- Edit files (click "View")
- Delete files/directories
- Create directories

## Architecture

```
User Browser
    ↓
┌─────────────────────────┐
│   Terminal UI (HTML)    │  ← bash_terminal.html
│  • Terminal Panel       │
│  • Script Manager       │
│  • File Browser         │  
│  • Modals               │
└──────────┬──────────────┘
           ↓ (AJAX)
┌─────────────────────────┐
│   Flask Routes (app.py) │  ← /api/terminal/*
│  • /api/terminal/*      │
│  • /bash-terminal/*     │  ← /bash-terminal/*
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│  Terminal Runtime       │  ← bash_terminal_runtime.py
│  • Command Execution    │
│  • Script Management    │
│  • File Operations      │
│  • Security Validation  │
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│   System Resources      │
│  • bash subprocess      │
│  • File System          │
│  • Script Directory     │  → /scripts
└─────────────────────────┘
```

## Key Components

### 1. Backend (`bash_terminal_runtime.py`)
- Execute bash commands with timeout
- Save/load/delete scripts with metadata
- Browse files and directories
- Create/delete files and directories
- Security: path validation, output escaping

### 2. Frontend (`bash_terminal.html`)
- Terminal output display
- Command input with Enter support
- Real-time script management
- File browser with navigation
- Modal editors for scripts and files
- Vanilla JavaScript (no jQuery)

### 3. Routes (in `app.py`)
- GET `/terminal` - Render UI
- POST `/api/terminal/execute` - Run commands
- POST `/api/terminal/scripts/create` - Save scripts
- POST `/api/terminal/scripts/<name>/execute` - Run scripts
- File operation endpoints
- Toggle endpoint

### 4. Configuration (`config.py`)
- `BASH_TERMINAL_ENABLED` - Feature toggle
- `BASH_TERMINAL_SCRIPT_DIR` - Script directory
- Validation and logging

## Features Comparison

| Feature | Tasks | Bash Terminal |
|---------|-------|---------------|
| Execute Commands | Python script | Any bash command |
| Real-time Output | ✅ | ✅ |
| File Management | Limited | Full file browser |
| Script Creation | ✅ | ✅ |
| Script Execution | ✅ | ✅ |
| Cron Scheduling | ✅ | ✅ (optional) |
| Metadata | Task name, URL | Script name, description, cron |
| State Persistence | Files | File + JSON metadata |
| Working Directory | Task folder | User-selectable |

## Security Model

### Default: Disabled
- Feature completely disabled
- No terminal tab visible
- No terminal routes accessible
- Zero security impact

### When Enabled
- Requires authentication (if enabled)
- Path traversal prevention
- Blocked directories: `/`, `/etc`, `/sys`, `/proc`, `/dev`, `/boot`, `/root`
- Command timeout: 30 seconds
- File read limit: 1MB
- HTML output escaping
- All operations logged

### Best Practices
1. Enable only when needed
2. Ensure authentication is ON
3. Monitor logs regularly
4. Review saved scripts
5. Test commands before running in production

## File Structure

```
Artillery/
├── app.py                           Main Flask app (UPDATED)
│   ├── Terminal routes (+250 lines)
│   ├── Toggle endpoint
│   └── Context processor
│
├── config.py                        Configuration (UPDATED)
│   ├── BASH_TERMINAL_ENABLED
│   └── BASH_TERMINAL_SCRIPT_DIR
│
├── bash_terminal_runtime.py         NEW CORE MODULE
│   ├── execute_command()
│   ├── save_script()
│   ├── get_script_content()
│   ├── list_directory()
│   ├── get_file_content()
│   └── ... (14 functions total)
│
├── templates/
│   ├── bash_terminal.html           NEW TERMINAL UI (570 lines)
│   │   ├── Terminal panel
│   │   ├── Scripts section
│   │   ├── File browser
│   │   └── Modals
│   ├── base.html                    UPDATED (navbar tab)
│   └── config.html                  UPDATED (control panel)
│
└── Documentation/
    ├── BASH_TERMINAL_FEATURE.md          Comprehensive guide
    ├── BASH_TERMINAL_QUICKSTART.md       Quick start
    ├── IMPLEMENTATION_SUMMARY.md         Technical summary
    └── IMPLEMENTATION_CHECKLIST.md       Checklist
```

## Example Usage

### Execute a One-liner
```bash
$ curl https://api.example.com/data | jq '.items | length'
```

### Create and Schedule a Backup Script
```bash
#!/bin/bash
# Filename: backup.sh
# Cron: 0 2 * * * (2 AM daily)

DATE=$(date +%Y%m%d)
tar -czf /backups/data-$DATE.tar.gz /data
echo "Backup completed: data-$DATE.tar.gz"
```

### Monitor System
```bash
$ watch -n 5 'df -h; echo ---; free -h; echo ---; ps aux --sort=-%mem | head -5'
```

### Manage Docker
```bash
# List running containers
$ docker ps

# Check container logs
$ docker logs my-container

# Execute command in container
$ docker exec -it my-container bash
```

## Environment Setup

### Docker Example
```dockerfile
FROM python:3.9-slim

ENV BASH_TERMINAL_ENABLED=0                    # Disabled by default
ENV BASH_TERMINAL_SCRIPT_DIR=/scripts

# ... rest of Dockerfile

CMD ["python", "app.py"]
```

### Docker Compose Example
```yaml
services:
  artillery:
    image: artillery:latest
    environment:
      BASH_TERMINAL_ENABLED: "0"               # Disabled
      BASH_TERMINAL_SCRIPT_DIR: "/scripts"
    volumes:
      - ./scripts:/scripts
      - ./tasks:/tasks
      - ./config:/config
      - ./downloads:/downloads
```

## Performance Impact

- **When Disabled**: Zero overhead
- **When Enabled but Idle**: Minimal (just context processor)
- **Active Command**: Real-time execution, output streaming
- **Script Execution**: Subprocess, non-blocking
- **File Operations**: On-demand loading

## Compatibility

- ✅ Python 3.8+
- ✅ Flask 2.0+
- ✅ Bootstrap 5.3+
- ✅ Modern browsers (Chrome, Firefox, Safari, Edge)
- ✅ Linux/Unix systems
- ✅ Docker containers
- ✅ Kubernetes pods

## Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| Terminal tab not visible | Check `BASH_TERMINAL_ENABLED=1` |
| Command times out | Increase timeout or use script |
| File not found | Verify path with `pwd` and `ls` |
| Permission denied | Check file permissions with `ls -la` |
| Script not saving | Check `/scripts` directory exists |

## Next Steps

1. **Enable the Feature**
   ```bash
   export BASH_TERMINAL_ENABLED=1
   ```

2. **Start Artillery**
   ```bash
   python app.py
   ```

3. **Open Terminal Tab**
   - Visit http://localhost:5000
   - Click Terminal in navbar

4. **Try It Out**
   - Execute: `ls`, `pwd`, `date`
   - Create script: `echo_hello.sh`
   - Browse files: Check `/tmp` directory

5. **Read Full Docs**
   - `BASH_TERMINAL_FEATURE.md` - Complete guide
   - `BASH_TERMINAL_QUICKSTART.md` - Quick examples

## Support

For issues or questions:
1. Check `BASH_TERMINAL_FEATURE.md` troubleshooting section
2. Review logs: `grep -i "bash" app.log`
3. Test configuration: `python -c "from config import Config; Config.from_env()"`

---

**Status: ✅ PRODUCTION READY**

The bash terminal feature is fully implemented, documented, tested, and ready for production use. Enable it safely by setting `BASH_TERMINAL_ENABLED=1` when you need shell access.
