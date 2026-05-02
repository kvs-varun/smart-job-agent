"""
Smart Job Agent V2 — Clean startup script.
Kills any existing processes on port 8000 then starts fresh uvicorn WITHOUT --reload.
Run from project root: .venv\\Scripts\\python start_v2.py
"""
import subprocess
import sys
import os
import time

PORT = 8000


def kill_port(port: int):
    """Kill ALL processes using the given port on Windows (two passes)."""
    killed = set()
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True
            )
            pids = set()
            for line in result.stdout.splitlines():
                if f":{port}" in line:
                    parts = line.strip().split()
                    if parts:
                        pid = parts[-1]
                        if pid.isdigit() and pid != "0" and pid not in killed:
                            pids.add(pid)
            if not pids:
                break
            for pid in pids:
                r = subprocess.run(
                    ["taskkill", "/F", "/PID", pid], capture_output=True, text=True
                )
                if r.returncode == 0:
                    print(f"  Killed PID {pid}")
                    killed.add(pid)
            time.sleep(1.5)
        except Exception as e:
            print(f"  Warning: kill attempt {attempt+1} failed: {e}")
            break


def check_port_free(port: int) -> bool:
    """Return True if port is free."""
    result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            return False
    return True


print("=" * 55)
print("  Smart Job Agent V2 — Starting")
print("=" * 55)

# Kill old processes
print(f"\n[1] Clearing port {PORT}...")
kill_port(PORT)
time.sleep(0.5)

if check_port_free(PORT):
    print(f"  Port {PORT} is free.")
else:
    print(f"  WARNING: Port {PORT} still in use — trying once more...")
    kill_port(PORT)
    time.sleep(2)
    if not check_port_free(PORT):
        print(f"  ERROR: Cannot free port {PORT}. Kill the process manually:")
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if f":{PORT}" in line and "LISTENING" in line:
                print(f"    {line.strip()}")
        print("  Then run: .venv\\Scripts\\python start_v2.py")
        sys.exit(1)

# Validate import works
print("\n[2] Validating import...")
result = subprocess.run(
    [sys.executable, "-c",
     "from backend_v2.main import app; routes=[r.path for r in app.routes]; "
     "print('Routes:', len(routes)); "
     "print('parse-resume:', '/v2/agent/parse-resume' in routes); "
     "print('build-resume:', '/v2/agent/build-resume' in routes)"],
    capture_output=True, text=True,
    cwd="D:/smart-job-agent"
)
print(result.stdout)
if result.returncode != 0:
    print("IMPORT FAILED:")
    print(result.stderr[-2000:])
    sys.exit(1)

# Start uvicorn WITHOUT --reload (avoids .pyc cache issues)
print("\n[3] Starting uvicorn (no --reload)...")
print("    Access: http://localhost:8000")
print("    Docs:   http://localhost:8000/docs")
print("    Stop:   Ctrl+C\n")

os.execv(
    sys.executable,
    [
        sys.executable, "-m", "uvicorn",
        "backend_v2.main:app",
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "--log-level", "info",
    ]
)
