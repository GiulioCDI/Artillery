# Bash Terminal - Quick Start Guide

## Enable the Feature

### Option 1: Environment Variable (Recommended)

```bash
export BASH_TERMINAL_ENABLED=1
python app.py
```

### Option 2: Toggle in UI (Runtime)

1. Navigate to **Config** tab
2. Scroll to "Bash Terminal (Advanced)" section
3. Click the toggle button
4. Terminal tab appears immediately in navbar

## Using the Terminal

### Execute Commands

```bash
# Type in the command input field
ls -la /home
pwd
docker ps
systemctl status nginx
```

**Working Directory:**
- Change directory in the "Working Directory" field
- Commands execute in that directory
- Default: `/root`

### Create and Run Scripts

**Create a Script:**
1. Click "New Script" in the Saved Scripts panel
2. Enter filename (e.g., `backup.sh`)
3. Add description: "Daily backup script"
4. Optional: Set cron schedule (e.g., `0 2 * * *` for 2 AM daily)
5. Write your bash code
6. Click "Save Script"

**Example Script:**
```bash
#!/bin/bash
echo "Starting backup..."
tar -czf /backups/data-$(date +%Y%m%d).tar.gz /data
echo "Backup completed"
```

**Run a Script:**
- Click "Run" button next to the script name
- Output appears in the terminal panel

### File Management

**Browse Files:**
1. Enter path in "Path" field (e.g., `/home/user`)
2. Click "Go" to navigate
3. See files and folders in the table

**Edit Files:**
1. Click "View" on any file
2. Modal opens with file content
3. Edit and click "Save File"

**Delete Files:**
1. Click "Del" next to any file
2. Confirm deletion
3. File is removed

**Create Directory:**
1. Enter path in terminal: `mkdir /path/to/new/dir`
2. Or use file browser to navigate and create

## Cron Scheduling

Scripts can be scheduled via cron format when created:

```
# Format: minute hour day month weekday
0 2 * * *       # 2 AM daily
*/15 * * * *    # Every 15 minutes
0 0 1 * *       # First day of month
0 9-17 * * 1-5  # 9 AM to 5 PM, weekdays
```

**Note:** Requires integration with scheduler.py for actual execution.

## Security Tips

⚠️ **Important:**
- Feature is disabled by default
- Enable only for trusted users
- Every command is logged
- Be cautious with destructive commands (rm, dd, etc.)
- Avoid running as root if possible

**Sensitive Operations:**
```bash
# Safe approach: Always test first
ls /path/to/data      # List before deleting
du -sh /path          # Check size before operations
```

## Common Commands

### System Information
```bash
uname -a              # System info
df -h                 # Disk usage
top -bn1 | head -20   # CPU/memory
```

### File Operations
```bash
find /data -type f -name "*.jpg"     # Find files
cp -r /src /dst                      # Copy
mv /old /new                         # Move
chmod 755 /script.sh                 # Permissions
```

### Docker
```bash
docker ps                            # List containers
docker logs container_name           # View logs
docker exec -it container_name bash  # Enter container
```

### Network
```bash
ping -c 5 example.com               # Test connectivity
curl -I https://example.com         # Check URL
netstat -tuln                       # Network connections
```

## Troubleshooting

### Terminal Tab Not Visible

**Check if feature is enabled:**
```bash
# In another terminal/container
echo $BASH_TERMINAL_ENABLED
# Should output: 1 or true
```

**Restart application:**
- If you changed the environment variable, restart app.py

### Command Timeout

Commands have a 30-second timeout by default. For longer operations:
- Create a script and run it instead (can run up to 300s)
- Or run in background: `nohup ./long_command.sh > output.log 2>&1 &`

### File Not Found

- Use file browser to navigate and verify path
- Check file permissions: `ls -la /path/to/file`
- Try running as different user if permission denied

### Script Not Saving

Check the following:
- Filename ends with `.sh`
- Script directory `/scripts` is writable
- No special characters in filename (except `-` and `_`)

**Check script directory:**
```bash
ls -la /scripts
# Should show your saved scripts
```

## Example Workflows

### Workflow 1: Daily Backups

1. Create script `daily_backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" /data
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete
echo "Backup completed: backup_$DATE.tar.gz"
```

2. Set cron: `0 2 * * *` (2 AM daily)
3. Test: Click "Run" to verify
4. Check logs in `/backups` directory

### Workflow 2: Docker Management

1. Create script `docker_cleanup.sh`:
```bash
#!/bin/bash
echo "Stopping unused containers..."
docker container prune -f
echo "Removing dangling images..."
docker image prune -f
echo "Cleanup complete"
```

2. Run manually or schedule: `0 3 * * 0` (3 AM on Sundays)

### Workflow 3: Log Analysis

1. In terminal, navigate to logs:
```bash
cd /var/log
ls -lh *.log
tail -100 syslog | grep ERROR
```

2. Create script for regular analysis:
```bash
#!/bin/bash
grep ERROR /var/log/application.log | tail -20 > /tmp/errors.txt
cat /tmp/errors.txt
```

## Performance Notes

- Commands execute in shells with standard bash
- File browser loads directory contents on demand
- Script execution runs in separate process
- Terminal output limited to prevent memory issues
- Timeout prevents hung processes

## Getting Help

**Check logs:**
```bash
# In terminal
tail -100 /path/to/app.log
# Look for Bash Terminal entries
```

**Test connectivity:**
```bash
ping localhost
curl http://localhost:5000/api/terminal/scripts
# Should return JSON if working
```

**Verify installation:**
```bash
python -c "import bash_terminal_runtime; print('OK')"
```

## Advanced Usage

### Environment Variables in Scripts

```bash
#!/bin/bash
# Access environment in scripts
echo "User: $USER"
echo "Home: $HOME"
echo "PATH: $PATH"

# Set your own
MY_VAR="custom value"
echo $MY_VAR
```

### Piping and Redirection

```bash
# All standard bash features work
cat /var/log/app.log | grep ERROR | wc -l
ps aux > /tmp/processes.txt
find /data -type f | xargs ls -lh
```

### Multiple Commands

```bash
# Use semicolons or &&
cd /data && find . -name "*.old" && rm *.old
```

## Security Reminders

✅ **Do:**
- Test commands in safe directory first
- Use version control for important scripts
- Monitor terminal usage logs
- Verify scripts before scheduling

❌ **Don't:**
- Run untrusted scripts
- Store passwords in scripts
- Use `sudo` without understanding consequences
- Modify system files without backup

---

**Need more details?** See `BASH_TERMINAL_FEATURE.md` for complete documentation.
