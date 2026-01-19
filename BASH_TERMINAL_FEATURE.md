# Bash Terminal Feature - Implementation Guide

## Overview

The bash terminal is an **advanced feature** that provides direct shell access to the Artillery application. It allows users to:

- Execute arbitrary bash commands with real-time output
- Browse and manage files in the filesystem
- Create, edit, and run bash scripts
- Schedule scripts to run via cron

**Important**: This feature is disabled by default due to security implications.

## Feature Control

### Configuration

The bash terminal is controlled by the `BASH_TERMINAL_ENABLED` environment variable:

```bash
# Enable (default: disabled)
export BASH_TERMINAL_ENABLED=1
# or
export BASH_TERMINAL_ENABLED=true

# Disable (default)
export BASH_TERMINAL_ENABLED=0
# or
export BASH_TERMINAL_ENABLED=false
```

**Toggle at Runtime**: Users can enable/disable the feature from the **Config** tab without restarting:
- Navigate to Config → Bash Terminal (Advanced)
- Click the toggle button to enable/disable
- Changes take effect immediately

### Scripts Directory

By default, bash scripts are saved to `/scripts`. You can customize this:

```bash
export BASH_TERMINAL_SCRIPT_DIR=/path/to/scripts
```

This directory is auto-created if it doesn't exist and is validated at startup.

## User Interface

### Terminal Tab

When enabled, a **Terminal** tab appears in the navbar (between Tasks and Config).

The terminal interface includes:

1. **Terminal Output Panel**
   - Live execution output
   - Colored text support (success, error, warning)
   - Auto-scroll toggle
   - Clear button to reset output

2. **Command Execution**
   - Enter bash commands in the input field
   - Specify working directory
   - Execute with Enter key or Run button
   - Real-time output display with exit codes

3. **Saved Scripts Panel**
   - List of all saved scripts with descriptions
   - Quick actions: Run, Edit, Delete
   - Create new scripts button
   - Scripts stored with metadata (description, cron schedule)

4. **File Browser**
   - Navigate filesystem
   - View file/directory details
   - Double-click to open directories
   - Edit, view, and delete files
   - Create new directories
   - Parent directory navigation

### Script Management

#### Creating Scripts

1. Click "New Script" in the Terminal tab
2. Enter script filename (must end with `.sh`)
3. Add optional description and cron schedule
4. Write bash code
5. Click "Save Script"

Scripts are saved to the configured script directory with metadata (description, cron schedule).

#### Editing Scripts

1. Click "Edit" on any script in the saved scripts list
2. Modify the content and metadata
3. Save changes

#### Running Scripts

1. Click "Run" on any script in the saved scripts list, or
2. Execute via terminal: `bash /scripts/my_script.sh`

Output appears in the terminal panel.

#### Scheduling Scripts

Scripts can be scheduled using standard cron format in the cron schedule field:

- `0 2 * * *` - Run daily at 2 AM
- `*/15 * * * *` - Run every 15 minutes
- `0 0 1 * *` - Run monthly on the 1st

**Note**: Cron integration requires scheduler.py to be configured to execute bash scripts.

## Architecture

### Backend Components

#### `bash_terminal_runtime.py`

Core module handling all terminal operations:

- **Command Execution**: `execute_command()` - Run bash commands with timeout
- **Script Management**: Functions to save, load, delete, and execute scripts
- **File Operations**: List, read, write, and delete files
- **Directory Operations**: Create and remove directories
- **Security**: Path traversal prevention, HTML escaping

#### Routes in `app.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/terminal` | GET | Render terminal page |
| `/api/terminal/execute` | POST | Execute bash command |
| `/api/terminal/list-dir` | POST | List directory contents |
| `/api/terminal/read-file` | POST | Read file content |
| `/api/terminal/write-file` | POST | Write file content |
| `/api/terminal/scripts` | GET | List saved scripts |
| `/api/terminal/scripts/create` | POST | Create/save script |
| `/api/terminal/scripts/<filename>` | GET | Get script content |
| `/api/terminal/scripts/<filename>/delete` | POST | Delete script |
| `/api/terminal/scripts/<filename>/execute` | POST | Execute script |
| `/api/terminal/delete-file` | POST | Delete file |
| `/api/terminal/delete-directory` | POST | Delete directory |
| `/api/terminal/create-directory` | POST | Create directory |
| `/bash-terminal/toggle` | POST | Toggle feature enable/disable |

### Frontend Components

#### `templates/bash_terminal.html`

Complete terminal interface with:

- Terminal output display
- Command input with history (Enter to execute)
- Real-time script management
- File browser with navigation
- Modal dialogs for script/file editing
- jQuery-free vanilla JavaScript

Features:
- Auto-scroll toggle
- Syntax highlighting for common log levels
- Responsive design
- Dark theme integration

## Security Considerations

### Access Control

- Feature is disabled by default
- Requires authentication (if enabled)
- Disabled on all routes when `BASH_TERMINAL_ENABLED=0`

### Path Security

- Path traversal prevention using relative path validation
- Scripts only stored in configured script directory
- File operations restricted to accessible paths
- Blocked directories: `/`, `/etc`, `/sys`, `/proc`, `/dev`, `/boot`, `/root`

### Output Safety

- HTML entities escaped in output (`&`, `<`, `>`, `"`, `'`)
- ANSI escape sequences handled safely
- Command output size limited (1MB for file reads)

### Command Execution

- Commands run with configurable timeout (default 30s, max 300s)
- Subprocess spawned with shell=True (requires careful input validation)
- Exit codes tracked and displayed

### Recommendations

1. **Enable only when needed** - Disable in production if not required
2. **Restrict access** - Ensure authentication is enabled
3. **Monitor usage** - Check logs for suspicious commands
4. **Audit scripts** - Review saved scripts regularly
5. **Limit scope** - Users can access files they have permissions for

## Configuration Integration

### config.py Updates

Added to `Config` dataclass:

```python
bash_terminal_enabled: bool  # Feature toggle
bash_terminal_script_dir: Path  # Directory for saved scripts
```

Validation:
- Directory auto-created if missing
- Directory write permissions verified at startup
- Boolean values: accepts "1/0", "true/false", "yes/no", "on/off"

### Environment Variables

```bash
BASH_TERMINAL_ENABLED=1                           # Enable feature
BASH_TERMINAL_SCRIPT_DIR=/scripts                 # Script directory
```

### Context Processing

Feature status available in all templates via `{{ bash_terminal_enabled }}`:

```html
{% if bash_terminal_enabled %}
  <a href="{{ url_for('terminal_page') }}">Terminal</a>
{% endif %}
```

## File Structure

```
/workspaces/Artillery/
├── bash_terminal_runtime.py      # Core terminal logic
├── app.py                        # Flask routes (updated)
├── config.py                     # Configuration (updated)
├── templates/
│   ├── bash_terminal.html        # Terminal UI
│   ├── base.html                 # Updated navbar
│   └── config.html               # Updated config panel
└── BASH_TERMINAL_FEATURE.md      # This file
```

## Database Schema

No database changes required. Scripts stored as files:

```
/scripts/
├── script1.sh
├── script1.json              # Metadata: description, cron
├── script2.sh
└── script2.json
```

Metadata format:

```json
{
  "name": "script_name",
  "description": "What this script does",
  "cron_schedule": "0 2 * * *",
  "created_at": "2026-01-15T10:30:00",
  "modified_at": "2026-01-15T10:30:00"
}
```

## Usage Examples

### Execute a Command

```javascript
// JavaScript example
fetch('/api/terminal/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    command: 'ls -la /home',
    cwd: '/home'
  })
}).then(r => r.json()).then(data => {
  console.log(data.stdout);  // Output
  console.log(data.returncode);  // Exit code
});
```

### Save a Script

```javascript
fetch('/api/terminal/scripts/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    filename: 'backup.sh',
    content: '#!/bin/bash\ntar -czf backup.tar.gz /data',
    description: 'Backup data directory',
    cron_schedule: '0 2 * * *'  // 2 AM daily
  })
}).then(r => r.json());
```

## Logging

All terminal activities logged at appropriate levels:

- `INFO`: Script operations, file operations
- `WARNING`: Path traversal attempts, permission errors
- `ERROR`: Command execution failures, I/O errors
- `DEBUG`: Individual file operations (if enabled)

Example log entries:

```
INFO: Script saved: backup.sh
WARNING: Attempted path traversal: ../../../etc/passwd
ERROR: Failed to delete file /root/protected: Permission denied
```

## Testing

### Manual Testing

1. Start Artillery with feature enabled:
   ```bash
   export BASH_TERMINAL_ENABLED=1
   python app.py
   ```

2. Navigate to Terminal tab
3. Test basic commands: `ls`, `pwd`, `date`
4. Test file operations: Create, edit, delete files
5. Test scripts: Save and execute a simple script

### Unit Testing

To test individual functions:

```python
from bash_terminal_runtime import execute_command, save_script

# Test command execution
stdout, stderr, code = execute_command("echo hello")
assert code == 0
assert "hello" in stdout

# Test script save
success, msg = save_script("test.sh", "#!/bin/bash\necho test", "Test script")
assert success
```

## Future Enhancements

Potential improvements:

1. **Terminal Sessions**: Persistent bash session state
2. **Script Scheduling**: Full cron integration with scheduler.py
3. **Terminal History**: Save command history
4. **Syntax Highlighting**: Code editor with syntax highlighting
5. **Terminal Recording**: Record and replay terminal sessions
6. **Permissions**: Fine-grained access control per user
7. **Audit Logging**: Detailed audit trail of all commands

## Troubleshooting

### Terminal Tab Not Visible

- Check `BASH_TERMINAL_ENABLED` is set to `1` or `true`
- Verify environment variable is loaded: `python -c "from config import Config; print(Config.from_env().bash_terminal_enabled)"`
- Restart application after changing config

### Commands Not Executing

- Check logs for permission errors
- Verify working directory exists and is accessible
- Check command syntax - run locally to verify
- Increase timeout if command takes longer than 30s

### Scripts Not Saving

- Check `/scripts` directory exists and is writable
- Check filename ends with `.sh`
- Check filename doesn't contain special characters
- Check disk space availability

### File Browser Shows Empty

- Check directory permissions
- Verify path is accessible
- Check for hidden files (start with `.`)

## References

- [bash_terminal_runtime.py](bash_terminal_runtime.py) - Core implementation
- [app.py](app.py) - Flask routes and integration
- [config.py](config.py) - Configuration validation
- [templates/bash_terminal.html](templates/bash_terminal.html) - UI implementation
