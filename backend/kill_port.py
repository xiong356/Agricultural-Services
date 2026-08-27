"""Kill all processes listening on port 8000"""
import subprocess
import re

# Find all PIDs listening on port 8000
result = subprocess.run(
    ["netstat", "-ano"],
    capture_output=True,
    encoding="gbk",
    errors="replace"
)

killed = []
for line in result.stdout.split("\n"):
    if ":8000" in line and "LISTENING" in line:
        match = re.search(r"\s+(\d+)$", line.strip())
        if match:
            pid = match.group(1)
            print(f"Killing PID {pid}...")
            subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
            killed.append(pid)

if not killed:
    print("No processes found on port 8000. Port is free!")
else:
    print(f"Killed {len(killed)} processes: {killed}")
