import subprocess
import time
import sys
import os
import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    if is_port_in_use(port):
        print(f"Port {port} is in use. Attempting to clear...")
        sys.stdout.flush()
        if os.name == 'nt':
            # Windows
            result = subprocess.run(['netstat', '-ano', '|', 'findstr', f':{port}'], capture_output=True, text=True, shell=True)
            for line in result.stdout.splitlines():
                if 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    print(f"Killing process {pid} on port {port}...")
                    sys.stdout.flush()
                    subprocess.run(['taskkill', '/F', '/PID', pid, '/T'], capture_output=True)
        else:
            # Unix/macOS
            subprocess.run(['fuser', '-k', f'{port}/tcp'], capture_output=True)
        time.sleep(1)

def run_services():
    print("\n" + "="*50)
    print("      CIVIC-AI PRO: LEGAL SUITE LAUNCHER")
    print("="*50 + "\n")
    sys.stdout.flush()
    
    # Pre-launch port cleanup
    kill_process_on_port(8000)
    kill_process_on_port(8502)
    
    # Ensure tables are initialized
    print("[1/3] Initializing Database...")
    sys.stdout.flush()
    try:
        import database
        database.init_db()
        print("      [OK] Database Ready.")
        sys.stdout.flush()
    except Exception as e:
        print(f"      [ERROR] Database Init Error: {e}")
        sys.stdout.flush()
        return

    # 1. Start Backend (FastAPI)
    print("\n[2/3] Starting FastAPI Backend on Port 8000...")
    sys.stdout.flush()
    backend_proc = subprocess.Popen(
        [sys.executable, "main.py"], 
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Give backend a moment to start
    time.sleep(3)
    
    # 2. Start Dashboard (Streamlit)
    print("[3/3] Starting Streamlit Dashboard on Port 8502...")
    sys.stdout.flush()
    dashboard_cmd = [sys.executable, "-m", "streamlit", "run", "main_app.py", "--server.port", "8502", "--server.headless", "false"]
    dashboard_proc = subprocess.Popen(
        dashboard_cmd, 
        cwd=os.getcwd(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    print("\n[SUCCESS] ALL SYSTEMS ONLINE")
    print("-" * 30)
    print(f"URL Dashboard:  http://localhost:8502")
    print(f"URL Backend API: http://localhost:8000")
    print("-" * 30)
    print("\nMonitoring services... Press Ctrl+C to shutdown.")
    sys.stdout.flush()
    
    # Use non-blocking read for pipes
    import threading
    def stream_logs(pipe, prefix):
        for line in iter(pipe.readline, ''):
            print(f"[{prefix}] {line.strip()}")
            sys.stdout.flush()

    threading.Thread(target=stream_logs, args=(backend_proc.stdout, "BACKEND"), daemon=True).start()
    threading.Thread(target=stream_logs, args=(dashboard_proc.stdout, "DASHBOARD"), daemon=True).start()

    try:
        while True:
            if backend_proc.poll() is not None:
                print("\n[CRITICAL] Backend stopped unexpectedly.")
                sys.stdout.flush()
                break
            if dashboard_proc.poll() is not None:
                print("\n[WARNING] Dashboard stopped unexpectedly.")
                sys.stdout.flush()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] SHUTTING DOWN...")
        sys.stdout.flush()
    finally:
        print("Cleaning up processes...")
        sys.stdout.flush()
        backend_proc.terminate()
        dashboard_proc.terminate()
        time.sleep(1)
        # Force kill if needed
        if backend_proc.poll() is None: backend_proc.kill()
        if dashboard_proc.poll() is None: dashboard_proc.kill()
        print("[DONE] Services stopped successfully.\n")
        sys.stdout.flush()

if __name__ == "__main__":
    print("Launcher script started...")
    sys.stdout.flush()
    run_services()
