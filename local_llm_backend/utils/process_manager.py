import subprocess
import os
import signal
import sys
from typing import Optional, Dict

class ProcessManager:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}

    def start_process(self, name: str, command: list[str], cwd: Optional[str] = None) -> bool:
        if name in self.processes and self.processes[name].poll() is None:
            print(f"Process {name} is already running.")
            return False

        try:
            # Use preexec_fn for Unix-like systems to create a new process group
            # This allows killing the process group to terminate all children
            preexec_fn = None
            if sys.platform != "win32":
                preexec_fn = os.setsid

            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, # Decode stdout/stderr as text
                bufsize=1, # Line-buffered
                universal_newlines=True, # Universal newlines for cross-platform compatibility
                preexec_fn=preexec_fn
            )
            self.processes[name] = process
            print(f"Process {name} started with PID: {process.pid}")
            return True
        except Exception as e:
            print(f"Error starting process {name}: {e}")
            return False

    def stop_process(self, name: str) -> bool:
        if name not in self.processes or self.processes[name].poll() is not None:
            print(f"Process {name} is not running.")
            return False

        process = self.processes[name]
        try:
            if sys.platform == "win32":
                # On Windows, kill the process tree
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], check=True, capture_output=True)
            else:
                # On Unix-like, kill the process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=10) # Wait for process to terminate
            print(f"Process {name} with PID {process.pid} stopped.")
            del self.processes[name]
            return True
        except (subprocess.CalledProcessError, ProcessLookupError, TimeoutError) as e:
            print(f"Error stopping process {name} (PID {process.pid}): {e}")
            # Ensure the process is removed from tracking even if it's stubborn
            if name in self.processes:
                del self.processes[name]
            return False
        except Exception as e:
            print(f"Unexpected error stopping process {name}: {e}")
            return False

    def get_process_status(self, name: str) -> str:
        if name not in self.processes:
            return "NOT_FOUND"
        if self.processes[name].poll() is None:
            return "RUNNING"
        return "STOPPED" # Process has terminated

    def get_process_output(self, name: str) -> tuple[str, str]:
        if name not in self.processes:
            return "", ""
        stdout, stderr = self.processes[name].communicate() # Note: communicate blocks until process terminates
        return stdout, stderr

    def list_running_processes(self) -> Dict[str, int]:
        running = {}
        for name, process in list(self.processes.items()): # Use list() to allow modification during iteration
            if process.poll() is None:
                running[name] = process.pid
            else:
                # Clean up processes that have terminated
                del self.processes[name]
        return running

process_manager = ProcessManager() # Global instance for convenience
