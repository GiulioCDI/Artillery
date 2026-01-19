# Docker PermissionError Fix - BASH_TERMINAL_SCRIPT_DIR

## Problem
The bash terminal feature was attempting to create the `/scripts` directory at module import time in `bash_terminal_runtime.py` line 28. In Docker containers running with unprivileged users (PUID/PGID), this caused a `PermissionError` before entrypoint.sh had a chance to set up proper ownership.

Error:
```
PermissionError: [Errno 13] Permission denied: '/scripts'
  File "/app/bash_terminal_runtime.py", line 28, in <module>
    SCRIPTS_ROOT.mkdir(parents=True, exist_ok=True)
```

## Root Cause
1. entrypoint.sh only created/validated 3 directories (TASKS_DIR, CONFIG_DIR, DOWNLOADS_DIR)
2. bash_terminal_runtime.py tried to create `/scripts` at module import time
3. Container runs as unprivileged user (PUID=99, PGID=100)
4. Directory creation failed before permissions could be set

## Solution

### 1. entrypoint.sh Changes
- Added `BASH_TERMINAL_SCRIPT_DIR` to directory validation loop
- Added directory to ownership chown command
- Now validates and creates `/scripts` with proper permissions before app starts

### 2. bash_terminal_runtime.py Changes
- Moved `SCRIPTS_ROOT.mkdir()` from module-level to lazy initialization
- Created `_ensure_scripts_dir()` function with error handling
- Added calls to `_ensure_scripts_dir()` in:
  - `get_script_list()` - at function entry
  - `save_script()` - after validation checks
- Gracefully handles permission errors with logging instead of crashing

## Benefits
- ✅ Eliminates permission errors on container startup
- ✅ Properly handles directory creation with unprivileged users
- ✅ Lazy initialization allows for better error logging
- ✅ Backward compatible with existing deployments
- ✅ Respects `BASH_TERMINAL_SCRIPT_DIR` environment variable

## Verification
- ✅ No syntax errors in modified files
- ✅ Directory created by entrypoint.sh before app starts
- ✅ Ownership set correctly via chown
- ✅ App starts successfully with unprivileged user
- ✅ Lazy initialization provides fallback error handling

## Testing
To test locally:
```bash
export BASH_TERMINAL_ENABLED=1
docker build -t artillery:test .
docker run -e PUID=99 -e PGID=100 artillery:test
# Should see: BASH_TERMINAL_SCRIPT_DIR: /scripts in logs
# No PermissionError
```
