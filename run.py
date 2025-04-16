import contextlib
import os
import sys
import logging
import socket
import subprocess
import threading
import time
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port."""
    current_port = start_port
    attempts = 0

    while attempts < max_attempts:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # Try binding to 127.0.0.1 first for stricter check
                try:
                    s.bind(('127.0.0.1', current_port))
                    logger.info(f"Port {current_port} is available on 127.0.0.1")
                    return current_port
                except OSError:
                     # If 127.0.0.1 fails, try 0.0.0.0 as a fallback check
                     s.close() # Close the previous socket
                     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_all:
                         s_all.bind(('0.0.0.0', current_port))
                         logger.info(f"Port {current_port} is available on 0.0.0.0")
                         return current_port
        except OSError:
            logger.warning(f"Port {current_port} is in use, trying next port")
            current_port += 1
            attempts += 1

    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")


def wait_for_frontend(frontend_port, max_attempts=30, timeout=5):
    """Wait until the frontend server is available."""
    for attempt in range(max_attempts):
        with contextlib.suppress(requests.RequestException):
            response = requests.get(f"http://127.0.0.1:{frontend_port}/", timeout=timeout) # Check localhost
            if response.status_code == 200:
                logger.info(f"Frontend is ready after {attempt+1} attempts")
                return True
        logger.info(f"Waiting for frontend to start (attempt {attempt+1}/{max_attempts})...")
        time.sleep(1)

    logger.warning("Frontend did not start in the expected time")
    return False

def start_frontend(frontend_port, backend_port):
    """Start the frontend application using npm."""
    project_root = Path(__file__).parent
    logger.info(f"Starting frontend from project root: {project_root} on port {frontend_port}")
    os.chdir(project_root)

    env = os.environ.copy()
    env["PORT"] = str(frontend_port)
    # Always use 127.0.0.1 for VITE_API_URL when running locally via run.py
    # The proxy target in vite.config.js should also point to 127.0.0.1
    env["VITE_API_URL"] = f"http://127.0.0.1:{backend_port}"
    env["VITE_BACKEND_PORT"] = str(backend_port)

    logger.info(f"Frontend environment variables: PORT={env['PORT']}, VITE_API_URL={env['VITE_API_URL']}, VITE_BACKEND_PORT={env['VITE_BACKEND_PORT']}")
    logger.info(f"Setting frontend API URL to: {env['VITE_API_URL']}")

    if not os.path.exists("node_modules"):
        logger.info("Installing frontend dependencies...")
        try:
            subprocess.run(["npm", "install", "--legacy-peer-deps"], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"npm install failed with legacy-peer-deps: {e.stderr}. Trying with force...")
            subprocess.run(["npm", "install", "--force"], check=True, capture_output=True, text=True)

    try:
        process = subprocess.Popen(
            ["npm", "run", "dev", "--", "--port", str(frontend_port), "--host", "0.0.0.0", "--strictPort", "false"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        if not process:
            logger.error("Failed to start frontend process")
            return None

        def log_output(process):
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        logger.info(f"FRONTEND: {line.strip()}")
                process.stdout.close()
            return_code = process.wait()
            if return_code != 0:
                logger.error(f"Frontend process exited with code {return_code}")

        log_thread = threading.Thread(target=log_output, args=(process,), daemon=True) # Use daemon=True
        log_thread.start()
        return process
    except Exception as e:
        logger.error(f"Error starting frontend: {e}")
        return None

def start_backend(backend_port):
    """Start the backend using uvicorn as a subprocess."""
    logger.info(f"Starting backend process on port {backend_port} with host 127.0.0.1")
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "app.api:app",
        "--host", "127.0.0.1", # Use localhost binding
        "--port", str(backend_port)
    ]
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
        if not process:
            logger.error("Failed to start backend process")
            return None

        def log_output(process):
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        logger.info(f"BACKEND: {line.strip()}")
                process.stdout.close()
            return_code = process.wait()
            if return_code != 0:
                logger.error(f"Backend process exited with code {return_code}")

        log_thread = threading.Thread(target=log_output, args=(process,), daemon=True) # Use daemon=True
        log_thread.start()
        return process
    except Exception as e:
        logger.error(f"Error starting backend process: {e}", exc_info=True)
        return None

def initialize_application():
    """Initialize the PolicyPulse application and set up ports."""
    logger.info("Starting PolicyPulse application")
    frontend_port = 5173
    backend_port = 8000
    frontend_port = find_available_port(frontend_port)
    backend_port = find_available_port(backend_port)
    os.environ["FRONTEND_PORT"] = str(frontend_port)
    os.environ["BACKEND_PORT"] = str(backend_port)
    logger.info(f"Using ports - Frontend: {frontend_port}, Backend: {backend_port}")
    return frontend_port, backend_port

def wait_for_backend(max_attempts=30, timeout=5):
    """Wait until the backend server is available."""
    backend_port = int(os.environ.get("BACKEND_PORT", 8000))
    url_to_check = f"http://127.0.0.1:{backend_port}/health/" # Check 127.0.0.1

    for attempt in range(max_attempts):
        try:
            response = requests.get(url_to_check, timeout=timeout)
            # ONLY accept 200 OK as a sign the backend is truly ready
            if response.status_code == 200:
                logger.info(f"Backend is ready after {attempt+1} attempts (URL: {url_to_check})")
                return True
            else:
                 logger.warning(f"Backend check failed on attempt {attempt+1}/{max_attempts}. Status: {response.status_code} (URL: {url_to_check})")
        except requests.ConnectionError:
            logger.info(f"Waiting for backend connection (attempt {attempt+1}/{max_attempts})... (URL: {url_to_check})")
        except requests.Timeout:
             logger.warning(f"Backend check timed out on attempt {attempt+1}/{max_attempts}. (URL: {url_to_check})")
        except Exception as e:
             logger.error(f"Unexpected error during backend check: {e} (URL: {url_to_check})")

        time.sleep(1) # Wait 1 second before retrying

    logger.error(f"Backend did not become ready at {url_to_check} after {max_attempts} attempts")
    return False


def print_service_urls(frontend_port, backend_port):
    """Print service URLs for easy access."""
    print("\n==== PolicyPulse Application Started ====")
    print(f"  - Backend API: http://127.0.0.1:{backend_port}") # Use 127.0.0.1
    print(f"  - Frontend UI: http://localhost:{frontend_port}") # Use localhost for frontend access
    print("=========================================\n")

def start_services(frontend_port, backend_port):
    """Start backend and frontend services as subprocesses and print access URLs."""
    backend_process = start_backend(backend_port)
    if not backend_process:
        logger.error("Failed to start backend process. Exiting.")
        sys.exit(1)

    if not wait_for_backend():
        logger.error("Backend failed to start correctly. Exiting.")
        if backend_process.poll() is None:
            backend_process.terminate()
        sys.exit(1)
    else:
         logger.info("Backend started successfully, now starting frontend...")

    frontend_process = start_frontend(frontend_port, backend_port)
    if not frontend_process:
        logger.error("Failed to start frontend process. Exiting.")
        if backend_process.poll() is None:
            backend_process.terminate()
        sys.exit(1)

    print_service_urls(frontend_port, backend_port)
    return backend_process, frontend_process

def main():
    try:
        frontend_port, backend_port = initialize_application()
        backend_process, frontend_process = start_services(frontend_port, backend_port)

        # Keep main thread alive while subprocesses run
        # Monitor frontend process; if it exits, terminate backend
        frontend_process.wait()
        logger.info("Frontend process exited.")

        if backend_process.poll() is None:
             logger.info("Terminating backend process...")
             backend_process.terminate()
             try:
                 backend_process.wait(timeout=5)
             except subprocess.TimeoutExpired:
                 logger.warning("Backend process did not terminate gracefully, killing.")
                 backend_process.kill()

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        # Ensure processes are terminated on Ctrl+C
        # Note: This might not always work perfectly depending on how processes handle SIGINT
        # Consider more robust signal handling if needed
    except Exception as e:
        logger.error(f"Error starting application: {e}", exc_info=True)
    finally:
        # Attempt cleanup, though processes might already be terminated
        logger.info("Performing final cleanup...")
        # Add any specific cleanup needed for backend_process or frontend_process if they exist
        # e.g., check if process handles exist and try to terminate/kill

if __name__ == "__main__":
    main()
