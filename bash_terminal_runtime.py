"""
Bash terminal runtime module for Artillery.

Manages bash script files, execution, and state for the terminal feature.
Provides file system operations, script management, and command execution.
"""

import os
import json
import logging
import subprocess
import threading
import time
import shlex
import uuid
import html
import pty
import select
import signal
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)

# Get directories from environment (set by app.py)
SCRIPTS_ROOT = Path(os.environ.get("BASH_TERMINAL_SCRIPT_DIR", "/scripts"))
TASKS_ROOT = Path(os.environ.get("TASKS_DIR", "/tasks"))


def _ensure_scripts_dir() -> bool:
    """Ensure scripts directory exists with proper permissions. Returns True on success."""
    try:
        SCRIPTS_ROOT.mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        logger.error(f"Permission denied creating scripts directory: {SCRIPTS_ROOT}")
        return False
    except Exception as e:
        logger.error(f"Failed to create scripts directory: {e}")
        return False

# Process tracking for running terminal commands
RUNNING_PROCESSES: Dict[str, subprocess.Popen] = {}
PROCESS_LOCK = threading.Lock()

# PTY session cleanup: remove idle finished sessions after this many seconds
PTY_SESSION_TTL_SECONDS = int(os.environ.get("PTY_SESSION_TTL_SECONDS", "300"))

# Blocked directories for security
BLOCKED_DIRECTORIES = {
    Path("/"),
    Path("/etc"),
    Path("/sys"),
    Path("/proc"),
    Path("/dev"),
    Path("/boot"),
    Path("/root"),
}


def _is_relative_to(path: Path, other: Path) -> bool:
    """Check if path is relative to other (Python 3.9+ compatible)."""
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def execute_command(command: str, cwd: Optional[str] = None, timeout: int = 300) -> Tuple[str, str, int]:
    """
    Execute a bash command and return stdout, stderr, and exit code.
    
    Args:
        command: Command string to execute
        cwd: Working directory for command execution
        timeout: Timeout in seconds (default 300s)
        
    Returns:
        Tuple of (stdout, stderr, exit_code)
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"Command timed out after {timeout} seconds", 124
    except Exception as e:
        return "", str(e), 1


def get_script_list() -> List[Dict]:
    """
    Get list of all saved bash scripts.
    
    Returns:
        List of script metadata dictionaries
    """
    scripts = []
    
    # Ensure scripts directory exists
    if not _ensure_scripts_dir():
        logger.warning("Could not ensure scripts directory exists")
        return scripts
    
    if not SCRIPTS_ROOT.exists():
        return scripts
    
    for script_file in sorted(SCRIPTS_ROOT.glob("*.sh")):
        try:
            meta_file = script_file.with_suffix(".json")
            
            # Get stats once for efficiency
            try:
                stat = script_file.stat()
            except FileNotFoundError:
                continue
            
            # Default metadata
            metadata = {
                "name": script_file.stem,
                "filename": script_file.name,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size,
                "description": "",
                "cron_schedule": "",
            }
            
            # Load metadata if it exists
            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8', errors='replace') as f:
                        stored_meta = json.load(f)
                        metadata.update(stored_meta)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {script_file.name}: {e}")
            
            scripts.append(metadata)
        except Exception as e:
            logger.warning(f"Failed to list script {script_file.name}: {e}")
    
    return scripts


def get_script_content(filename: str) -> Optional[str]:
    """
    Get the content of a saved script.
    
    Args:
        filename: Script filename
        
    Returns:
        Script content or None if not found
    """
    script_path = SCRIPTS_ROOT / filename
    
    # Security: prevent path traversal
    if not _is_relative_to(script_path.resolve(), SCRIPTS_ROOT.resolve()):
        logger.warning(f"Attempted path traversal: {filename}")
        return None
    
    if not script_path.exists():
        return None
    
    try:
        with open(script_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read script {filename}: {e}")
        return None


def _validate_cron_schedule(cron_str: str) -> bool:
    """
    Validate cron schedule format (basic validation).
    
    Accepts standard cron format: minute hour day month weekday
    Can be empty (not required).
    """
    if not cron_str or cron_str.strip() == "":
        return True  # Empty is OK
    
    parts = cron_str.strip().split()
    
    # Standard cron has 5 parts
    if len(parts) != 5:
        return False
    
    # Each part should be non-empty
    if any(not part for part in parts):
        return False
    
    return True


def save_script(filename: str, content: str, description: str = "", 
                cron_schedule: str = "") -> Tuple[bool, str]:
    """
    Save a bash script file with metadata.
    
    Args:
        filename: Script filename (must end with .sh)
        content: Script content
        description: Script description
        cron_schedule: Optional cron schedule
        
    Returns:
        Tuple of (success, message)
    """
    if not filename.endswith(".sh"):
        return False, "Script filename must end with .sh"
    
    if not filename.replace(".sh", "").replace("_", "").replace("-", "").isalnum():
        return False, "Script filename contains invalid characters"
    
    if cron_schedule and not _validate_cron_schedule(cron_schedule):
        return False, "Invalid cron schedule format (must be: minute hour day month weekday)"
    
    # Ensure scripts directory exists
    if not _ensure_scripts_dir():
        return False, "Could not access scripts directory"
    
    script_path = SCRIPTS_ROOT / filename
    
    # Security: prevent path traversal
    try:
        if not _is_relative_to(script_path.resolve(), SCRIPTS_ROOT.resolve()):
            logger.warning(f"Attempted path traversal: {filename}")
            return False, "Invalid script path"
    except ValueError:
        return False, "Invalid script path"
    
    try:
        # Write script content with atomic write
        tmp_path = script_path.with_suffix(".sh.tmp")
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Make script executable
        os.chmod(tmp_path, 0o755)
        
        # Atomic move
        tmp_path.replace(script_path)
        
        # Save metadata
        meta_file = script_path.with_suffix(".json")
        metadata = {
            "name": script_path.stem,
            "description": description,
            "cron_schedule": cron_schedule,
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
        }
        
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Script saved: {filename}")
        return True, f"Script saved: {filename}"
    except Exception as e:
        logger.error(f"Failed to save script {filename}: {e}")
        return False, f"Failed to save script: {e}"


def delete_script(filename: str) -> Tuple[bool, str]:
    """
    Delete a saved bash script.
    
    Args:
        filename: Script filename to delete
        
    Returns:
        Tuple of (success, message)
    """
    script_path = SCRIPTS_ROOT / filename
    
    # Security: prevent path traversal
    try:
        if not _is_relative_to(script_path.resolve(), SCRIPTS_ROOT.resolve()):
            logger.warning(f"Attempted path traversal: {filename}")
            return False, "Invalid script path"
    except ValueError:
        return False, "Invalid script path"
    
    try:
        if script_path.exists():
            script_path.unlink()
        
        # Delete metadata
        meta_file = script_path.with_suffix(".json")
        if meta_file.exists():
            meta_file.unlink()
        
        logger.info(f"Script deleted: {filename}")
        return True, f"Script deleted: {filename}"
    except Exception as e:
        logger.error(f"Failed to delete script {filename}: {e}")
        return False, f"Failed to delete script: {e}"


def list_directory(path: str = "/") -> Tuple[bool, List[Dict]]:
    """
    List directory contents for file browser.
    
    Args:
        path: Directory path to list
        
    Returns:
        Tuple of (success, file_list)
    """
    try:
        dir_path = Path(path).expanduser().resolve()
        
        # Security: prevent access to sensitive directories
        for blocked in BLOCKED_DIRECTORIES:
            if dir_path == blocked or (str(dir_path).startswith(str(blocked) + "/")):
                return False, []
        
        if not dir_path.is_dir():
            return False, []
        
        files = []
        for item in sorted(dir_path.iterdir()):
            try:
                # pathlib.Path.is_dir() does not accept follow_symlinks parameter
                is_dir = item.is_dir()
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": is_dir,
                    "size": item.stat().st_size if not is_dir else 0,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                })
            except PermissionError as e:
                logger.debug(f"Permission denied listing {item}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Failed to list item {item}: {e}")
        
        return True, files
    except Exception as e:
        logger.error(f"Failed to list directory {path}: {e}")
        return False, []


def get_file_content(filepath: str) -> Tuple[bool, str]:
    """
    Get content of a file (with size limit for safety).
    
    Args:
        filepath: Path to file
        
    Returns:
        Tuple of (success, content)
    """
    try:
        file_path = Path(filepath).expanduser().resolve()
        
        # Security: prevent reading sensitive files
        blocked_paths = {Path("/etc/shadow"), Path("/etc/passwd")}
        if file_path in blocked_paths:
            return False, "Access denied"
        
        # Size limit: 1MB
        if file_path.stat().st_size > 1024 * 1024:
            return False, "File too large (max 1MB)"
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return True, content
    except Exception as e:
        return False, str(e)


def save_file_content(filepath: str, content: str) -> Tuple[bool, str]:
    """
    Save content to a file.
    
    Args:
        filepath: Path to file
        content: File content
        
    Returns:
        Tuple of (success, message)
    """
    try:
        file_path = Path(filepath).expanduser().resolve()
        
        # Atomic write
        tmp_path = file_path.with_suffix(".tmp")
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Atomic move
        tmp_path.replace(file_path)
        
        return True, f"File saved: {filepath}"
    except Exception as e:
        logger.error(f"Failed to save file {filepath}: {e}")
        return False, f"Failed to save file: {e}"


def create_directory(dirpath: str) -> Tuple[bool, str]:
    """
    Create a directory.
    
    Args:
        dirpath: Directory path to create
        
    Returns:
        Tuple of (success, message)
    """
    try:
        dir_path = Path(dirpath).expanduser().resolve()
        dir_path.mkdir(parents=True, exist_ok=True)
        return True, f"Directory created: {dirpath}"
    except Exception as e:
        logger.error(f"Failed to create directory {dirpath}: {e}")
        return False, f"Failed to create directory: {e}"


def delete_file(filepath: str) -> Tuple[bool, str]:
    """
    Delete a file.
    
    Args:
        filepath: Path to file
        
    Returns:
        Tuple of (success, message)
    """
    try:
        file_path = Path(filepath).expanduser().resolve()
        
        if file_path.is_file():
            file_path.unlink()
            return True, f"File deleted: {filepath}"
        elif file_path.is_dir():
            return False, "Use directory delete for directories"
        else:
            return False, "File not found"
    except Exception as e:
        logger.error(f"Failed to delete file {filepath}: {e}")
        return False, f"Failed to delete file: {e}"


def delete_directory(dirpath: str) -> Tuple[bool, str]:
    """
    Delete a directory recursively.
    
    Args:
        dirpath: Directory path to delete
        
    Returns:
        Tuple of (success, message)
    """
    try:
        dir_path = Path(dirpath).expanduser().resolve()
        
        if dir_path.is_dir():
            import shutil
            shutil.rmtree(dir_path)
            return True, f"Directory deleted: {dirpath}"
        else:
            return False, "Directory not found"
    except Exception as e:
        logger.error(f"Failed to delete directory {dirpath}: {e}")
        return False, f"Failed to delete directory: {e}"


def escape_log_output(text: str) -> str:
    """Escape HTML special characters in log output."""
    return html.escape(text)


# =====================================================================
# PTY-based live terminal sessions
# =====================================================================

class PtySession:
    def __init__(self, session_id: str, process: subprocess.Popen, master_fd: int):
        self.session_id = session_id
        self.process = process
        self.master_fd = master_fd
        self.buffer = []  # type: list[str]
        self.lock = threading.Lock()
        self.exit_code: Optional[int] = None
        self.exited_at: Optional[float] = None

    def _collect_output(self) -> None:
        """Collect any available output into buffer."""
        with self.lock:
            try:
                while True:
                    rlist, _, _ = select.select([self.master_fd], [], [], 0)
                    if not rlist:
                        break
                    data = os.read(self.master_fd, 4096)
                    if not data:
                        break
                    self.buffer.append(data.decode(errors="replace"))
            except OSError:
                pass

    def read_output(self) -> Tuple[str, bool, Optional[int]]:
        """Return buffered output, running status, and exit code if finished."""
        self._collect_output()
        with self.lock:
            out = "".join(self.buffer)
            self.buffer.clear()
        running = self.process.poll() is None
        if not running and self.exit_code is None:
            self.exit_code = self.process.returncode
            self.exited_at = self.exited_at or time.time()
        return out, running, self.exit_code

    def write_input(self, data: str) -> None:
        try:
            os.write(self.master_fd, data.encode())
        except OSError:
            pass

    def send_signal(self, sig: signal.Signals) -> None:
        try:
            pgid = os.getpgid(self.process.pid)
            os.killpg(pgid, sig)
        except OSError:
            pass

    def close(self) -> None:
        try:
            self.send_signal(signal.SIGTERM)
        except Exception:
            pass
        try:
            if self.exit_code is None:
                self.exit_code = self.process.poll()
                if self.exit_code is not None:
                    self.exited_at = self.exited_at or time.time()
            os.close(self.master_fd)
        except OSError:
            pass

    def should_reap(self, ttl: int) -> bool:
        if self.exited_at is None:
            return False
        return (time.time() - self.exited_at) >= ttl


PTY_SESSIONS: Dict[str, PtySession] = {}
PTY_LOCK = threading.Lock()


def start_pty_session(cwd: Optional[str] = None) -> str:
    """Start a PTY-backed shell session and return the session ID.

    Raises ValueError for invalid working directories to surface a 4xx to clients.
    """
    reap_finished_pty_sessions()
    session_id = str(uuid.uuid4())[:12]
    master_fd, slave_fd = pty.openpty()

    try:
        if cwd:
            resolved_cwd = Path(cwd).expanduser().resolve()
            if not resolved_cwd.is_dir():
                raise ValueError(f"Working directory does not exist: {cwd}")
            cwd_path = str(resolved_cwd)
        else:
            cwd_path = os.path.expanduser("~")

        proc = subprocess.Popen(
            ["/bin/bash"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=cwd_path,
            preexec_fn=os.setsid,
            bufsize=0,
            text=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        os.close(slave_fd)
        os.close(master_fd)
        raise ValueError(f"Working directory does not exist: {cwd}")
    except Exception:
        os.close(slave_fd)
        os.close(master_fd)
        raise

    # Close slave in parent
    os.close(slave_fd)

    session = PtySession(session_id, proc, master_fd)
    with PTY_LOCK:
        PTY_SESSIONS[session_id] = session
    return session_id


def read_pty_output(session_id: str) -> Tuple[str, bool, Optional[int]]:
    reap_finished_pty_sessions()
    with PTY_LOCK:
        session = PTY_SESSIONS.get(session_id)
    if not session:
        return "", False, None
    output, running, exit_code = session.read_output()
    if not running and session.exited_at is None:
        session.exited_at = time.time()
    return output, running, exit_code


def write_pty_input(session_id: str, data: str) -> bool:
    with PTY_LOCK:
        session = PTY_SESSIONS.get(session_id)
    if not session:
        return False
    session.write_input(data)
    return True


def signal_pty(session_id: str, sig: signal.Signals) -> bool:
    with PTY_LOCK:
        session = PTY_SESSIONS.get(session_id)
    if not session:
        return False
    session.send_signal(sig)
    return True


def cleanup_pty(session_id: str) -> None:
    with PTY_LOCK:
        session = PTY_SESSIONS.pop(session_id, None)
    if session:
        session.close()


def reap_finished_pty_sessions(max_age_seconds: int = PTY_SESSION_TTL_SECONDS) -> None:
    """Remove finished PTY sessions that have been idle beyond TTL."""
    now = time.time()
    to_cleanup: List[str] = []
    with PTY_LOCK:
        for sid, session in list(PTY_SESSIONS.items()):
            if session.process.poll() is None:
                continue
            if session.exit_code is None:
                session.exit_code = session.process.returncode
                session.exited_at = session.exited_at or now
            if session.should_reap(max_age_seconds):
                to_cleanup.append(sid)

    for sid in to_cleanup:
        cleanup_pty(sid)


def has_pty_session(session_id: str) -> bool:
    with PTY_LOCK:
        return session_id in PTY_SESSIONS


# =====================================================================
# Async Script Execution (Background Tasks)
# =====================================================================

class AsyncExecution:
    """Tracks background script execution."""
    
    def __init__(self, exec_id: str, command: str, cwd: str, timeout: int):
        self.exec_id = exec_id
        self.command = command
        self.cwd = cwd
        self.timeout = timeout
        self.start_time = time.time()
        self.stdout = ""
        self.stderr = ""
        self.returncode = None
        self.status = "running"  # running, completed, failed, timeout
        self.error = None
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        elapsed = time.time() - self.start_time
        return {
            "exec_id": self.exec_id,
            "status": self.status,
            "elapsed_seconds": round(elapsed, 1),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "error": self.error,
        }


# Global tracking of async executions
_async_executions: Dict[str, AsyncExecution] = {}
_async_lock = threading.Lock()


def start_async_script(command: str, cwd: Optional[str] = None, timeout: int = 3600) -> str:
    """
    Start a script in the background and return execution ID immediately.
    
    Args:
        command: Command to execute
        cwd: Working directory
        timeout: Timeout in seconds
        
    Returns:
        Execution ID for polling status
    """
    exec_id = str(uuid.uuid4())[:12]
    exec_obj = AsyncExecution(exec_id, command, cwd or os.path.expanduser("~"), timeout)
    
    with _async_lock:
        _async_executions[exec_id] = exec_obj
    
    # Run in background thread
    thread = threading.Thread(
        target=_run_async_command,
        args=(exec_id, command, exec_obj.cwd, timeout),
        daemon=True
    )
    thread.start()
    
    return exec_id


def get_async_status(exec_id: str) -> Optional[Dict]:
    """Get status of a background execution."""
    with _async_lock:
        if exec_id not in _async_executions:
            return None
        return _async_executions[exec_id].to_dict()


def _run_async_command(exec_id: str, command: str, cwd: str, timeout: int):
    """Run command in background and update execution object."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        with _async_lock:
            if exec_id in _async_executions:
                exec_obj = _async_executions[exec_id]
                exec_obj.stdout = result.stdout
                exec_obj.stderr = result.stderr
                exec_obj.returncode = result.returncode
                exec_obj.status = "completed" if result.returncode == 0 else "failed"
    
    except subprocess.TimeoutExpired:
        with _async_lock:
            if exec_id in _async_executions:
                exec_obj = _async_executions[exec_id]
                exec_obj.error = f"Command timed out after {timeout} seconds"
                exec_obj.status = "timeout"
                exec_obj.returncode = 124
    
    except Exception as e:
        with _async_lock:
            if exec_id in _async_executions:
                exec_obj = _async_executions[exec_id]
                exec_obj.error = str(e)
                exec_obj.status = "failed"
                exec_obj.returncode = 1
