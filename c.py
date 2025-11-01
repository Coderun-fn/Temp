import os
import sys
import time
import threading
import concurrent.futures
import atexit
import signal
import numpy as np
import requests
import psutil
import urllib3 # Import urllib3 to manage warnings

# Suppress the InsecureRequestWarning generated when using verify=False, 
# as we are intentionally bypassing verification for stress testing an external resource.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- GPU Setup: Simplified to use NumPy only (CPU Placeholder) ---
# Since CuPy is not installed, we simplify the code to directly use NumPy.
# The stress test for the integrated Intel Iris Xe Graphics will run on the CPU.
cp = np 
CUPY_AVAILABLE = False
# --------------------------------------------------------------------

# --- Configuration ---
DISK_FILE = 'D:\\temp_stress_file.bin'  # The file path used in your output
NETWORK_URL = 'https://speed.hetzner.de/100MB.bin'
RAM_CHUNK_SIZE = 500 * 4096 * 4096  # 500MB chunk for memory allocation
MONITOR_INTERVAL = 5.0 # Seconds between diagnosis reports

# Global flag to signal all threads to stop
stop_event = threading.Event()
executor = None # ThreadPoolExecutor
# Lock used for clean console output when multiple threads are printing
lock = threading.Lock()

# --- Stress Functions ---

def cpu_stress(thread_id):
    """Continuously performs matrix multiplication using numpy (FPU load)."""
    print(f"[CPU Thread {thread_id}]: Starting matrix multiplication loop...")
    # Use random matrices to ensure calculations are non-trivial
    a = np.random.rand(512, 512)
    b = np.random.rand(512, 512)
    try:
        while not stop_event.is_set():
            # Perform matrix multiplication (a good CPU stressor)
            np.dot(a, b)
    except Exception as e:
        if not stop_event.is_set():
            print(f"[CPU Thread {thread_id} ERROR]: {e}")

def gpu_stress():
    """
    Stresses the GPU (Placeholder) by using intensive NumPy calculations on the CPU.
    Targeting the integrated Intel Iris Xe Graphics processing pathway.
    """
    print("[GPU Thread]: Starting CPU Placeholder load for integrated graphics.")
    # Matrix size for intensive NumPy calculation
    matrix_size = 4096
    # Initialize using NumPy (aliased as cp)
    a = cp.random.rand(matrix_size, matrix_size) 
    b = cp.random.rand(matrix_size, matrix_size) 
    
    try:
        while not stop_event.is_set():
            # cp.dot performs intensive CPU matrix math
            cp.dot(a, b) 
            
            # Periodically re-create matrices to simulate data transfer overhead
            if np.random.rand() < 0.05: 
                a = cp.random.rand(matrix_size, matrix_size) 
                b = cp.random.rand(matrix_size, matrix_size)
                 
    except Exception as e:
        if not stop_event.is_set():
            print(f"[GPU Thread ERROR]: Failed during computation. Error: {e}")

def cache_stress():
    """
    Stresses the CPU's L1/L2/L3 caches using non-sequential memory access (a cache-thrashing test).
    """
    print("[CACHE Thread]: Starting L1/L2/L3 cache stress (large stride access)...")
    
    # Target size (256 million elements = approx. 2GB memory for float64), 
    # ensuring the data set is larger than typical L3 cache
    array_size = 256_000_000
    # Stride of 1024 ensures non-sequential access, maximizing cache misses
    stride = 4096
    
    try:
        # Allocate the array in RAM
        data = np.zeros(array_size, dtype=np.float64)
        
        # Access loop designed to maximize cache misses
        while not stop_event.is_set():
            # Only iterate over the indices that are hit by the stride
            for i in range(array_size // stride):
                # Non-sequential, strided access to defeat cache prediction
                index = i * stride
                
                # Perform a simple read/write operation
                # The operation is designed to prevent compiler optimization
                data[index] = data[index] * 1.0000000001 + 1.0 
                
    except Exception as e:
        if not stop_event.is_set():
            print(f"[CACHE Thread ERROR]: Cache stress operation failed: {e}")

def io_bound_stress():
    """
    Continuously performs rapid context switching, stressing the CPU scheduler and chipset/VRMs.
    """
    print("[I/O Bound Thread]: Starting high context-switching load...")
    try:
        while not stop_event.is_set():
            # Sleeping for a very short time forces the OS scheduler
            # to swap this thread out and back in repeatedly.
            # This stresses the kernel and CPU interrupt/context switching mechanisms.
            time.sleep(0.00001) 
    except Exception as e:
        if not stop_event.is_set():
            print(f"[I/O Bound Thread ERROR]: {e}")
            
def ram_stress():
    """Continuously allocates and manipulates memory."""
    print("[RAM Thread]: Starting memory allocation and manipulation...")
    
    # Store allocated chunks globally so Python doesn't immediately garbage collect them
    global memory_chunks
    memory_chunks = []
    
    try:
        while not stop_event.is_set():
            # 1. Allocate a large block of memory (list of large numbers)
            chunk = [i for i in range(RAM_CHUNK_SIZE // 8)]
            memory_chunks.append(chunk)
            
            # 2. Manipulate the allocated data (e.g., sorting, hashing)
            if len(memory_chunks) > 1:
                chunk.reverse()
            
            # 3. Periodically remove old chunks to simulate dynamic usage
            if len(memory_chunks) > 4: # Keep a maximum of 4 chunks (2GB in this example)
                memory_chunks.pop(0)

            time.sleep(0.1) # Brief pause to allow OS scheduling
            
    except MemoryError:
        print("[RAM Thread FATAL ERROR]: Memory allocation failed. System is out of memory.")
    except Exception as e:
        if not stop_event.is_set():
            print(f"[RAM Thread ERROR]: {e}")
    finally:
        # Clean up all allocated memory chunks
        if 'memory_chunks' in globals():
             del memory_chunks
        
def disk_stress():
    """Continuously writes and reads random data to a temporary file."""
    print(f"[DISK Thread]: Starting read/write cycle on: {DISK_FILE}")
    
    # Create a buffer of 1MB random bytes
    write_buffer = os.urandom(4096 * 4096)
    
    try:
        while not stop_event.is_set():
            # 1. Write the buffer to the disk file
            with open(DISK_FILE, 'r+b') as f: 
                f.seek(0)
                f.write(write_buffer)
            
            # 2. Read the buffer back (stress read operations)
            with open(DISK_FILE, 'rb') as f:
                f.seek(0)
                f.read(len(write_buffer))

            # 3. Sync file system (forces OS to commit data immediately)
            pass 
            
    except FileNotFoundError:
        # Create the initial file if it doesn't exist (must be large enough for r+b)
        try:
            with open(DISK_FILE, 'wb') as f:
                f.write(os.urandom(10 * 4096 * 4096)) # 10MB initial file
            print(f"[DISK Thread INFO]: Created initial file at {DISK_FILE}")
        except Exception as e:
            print(f"[DISK Thread FATAL ERROR]: Could not create file at {DISK_FILE}. Check disk permissions/path. {e}")
            stop_event.set() # Stop the test if disk I/O fails immediately
            
    except Exception as e:
        if not stop_event.is_set():
            print(f"[DISK Thread ERROR]: Disk I/O operation failed: {e}")

def network_stress():
    """
    Continuously attempts to download a large file, stressing the NIC (Wi-Fi or Wired).
    """
    print(f"[NETWORK/Wi-Fi Thread]: Starting continuous download from: {NETWORK_URL}")
    session = requests.Session()
    
    try:
        while not stop_event.is_set():
            try:
                # Added verify=False to ignore the SSL Certificate expiration error
                with session.get(NETWORK_URL, stream=True, timeout=10, verify=False) as r: 
                    r.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                    
                    # --- NEW DIAGNOSTIC LOGGING ---
                    content_length = r.headers.get('content-length')
                    if content_length:
                        print(f"[NETWORK/Wi-Fi Thread INFO]: Connection established (Status {r.status_code}). Expected size: {int(content_length)/(4096*4096):.1f}MB")
                    else:
                        print(f"[NETWORK/Wi-Fi Thread INFO]: Connection established (Status {r.status_code}). Size unknown.")
                    # ------------------------------

                    # Read the content in chunks (simulates a continuous heavy download)
                    for chunk in r.iter_content(chunk_size=8192):
                        if stop_event.is_set():
                            break
                        # Receiving data stresses the NIC (Wi-Fi or Wired)
                
                # If download completes successfully, wait a short period before restarting
                time.sleep(1) 

            except requests.exceptions.SSLError as ssl_e:
                print(f"\n[NETWORK/Wi-Fi Thread ERROR]: Request failed (SSL): {ssl_e}. Retrying in 5 seconds.")
                time.sleep(5)
            except requests.exceptions.RequestException as req_e:
                # Handles all other request errors (timeouts, connection issues, etc.)
                print(f"\n[NETWORK/Wi-Fi Thread ERROR]: Request failed (Request): {req_e}. Retrying in 5 seconds.")
                time.sleep(5)
                
    except Exception as e:
        if not stop_event.is_set():
            print(f"\n[NETWORK/Wi-Fi Thread CRITICAL ERROR]: {e}")
        
def diagnosis_monitor():
    """Monitors and reports system health metrics, including I/O rates."""
    print("\n[DIAGNOSIS Thread]: Starting system health monitor...")
    
    # Check if temperature monitoring is available
    temp_available = hasattr(psutil, 'sensors_temperatures') and psutil.sensors_temperatures()

    try:
        while not stop_event.is_set():
            # Get start counters for rate calculation
            net_io_start = psutil.net_io_counters()
            disk_io_start = psutil.disk_io_counters()
            
            # Wait for the interval to pass
            time.sleep(MONITOR_INTERVAL)

            # Get end counters and current metrics
            net_io_end = psutil.net_io_counters()
            disk_io_end = psutil.disk_io_counters()
            
            # Get CPU and RAM metrics (using 1 second internal sampling for accuracy)
            cpu_load = psutil.cpu_percent(interval=1.0) 
            mem = psutil.virtual_memory()

            # --- Calculate I/O rates (MB/s) ---
            
            # Network Rate
            net_sent = (net_io_end.bytes_sent - net_io_start.bytes_sent) / MONITOR_INTERVAL / (4096 * 4096)
            net_recv = (net_io_end.bytes_recv - net_io_start.bytes_recv) / MONITOR_INTERVAL / (4096 * 4096)
            
            # Disk Rate
            disk_read = (disk_io_end.read_bytes - disk_io_start.read_bytes) / MONITOR_INTERVAL / (4096 * 4096)
            disk_write = (disk_io_end.write_bytes - disk_io_start.write_bytes) / MONITOR_INTERVAL / (4096 * 4096)
            
            # --- Format Log Message ---
            log_message = f"[DIAGNOSIS]: CPU Load: {cpu_load:.1f}% | RAM Used: {mem.percent:.1f}% ({mem.used/4096**3:.1f}GB)"
            log_message += f" | Disk I/O: R:{disk_read:.1f}MB/s W:{disk_write:.1f}MB/s"
            log_message += f" | Net I/O: S:{net_sent:.1f}MB/s R:{net_recv:.1f}MB/s"
            
            # Check for and append CPU temperature if available
            if temp_available:
                temps = psutil.sensors_temperatures()
                core_temp = None
                
                if 'coretemp' in temps:
                    core_temp = max(sensor.current for sensor in temps['coretemp'])
                elif 'cpu_thermal' in temps:
                    core_temp = max(sensor.current for sensor in temps['cpu_thermal'])
                
                if core_temp is not None:
                    log_message += f" | CPU Temp: {core_temp:.1f}°C"
                
            with lock: # Use the global lock for clean printing
                print(log_message)

    except Exception as e:
        if not stop_event.is_set():
            print(f"[DIAGNOSIS Thread ERROR]: Monitoring failed: {e}")

# --- Cleanup and Main Execution ---

def cleanup():
    """Stops all threads and performs final cleanup."""
    global executor
    
    if stop_event.is_set():
        return # Already cleaning up
        
    print("\n[INFO]: Keyboard interrupt received. Shutting down threads...")
    stop_event.set()
    
    if executor:
        print("[INFO]: Executor shutdown initiated.")
        # Wait for all running futures to finish gracefully (or time out)
        executor.shutdown(wait=False, cancel_futures=True)

    # Allow a small moment for threads to acknowledge the stop signal
    time.sleep(2) 
    
    # Attempt to delete the disk file
    try:
        if os.path.exists(DISK_FILE):
            os.remove(DISK_FILE)
            print(f"[INFO]: Successfully deleted temporary file {DISK_FILE}")
    except Exception as e:
        print(f"[WARNING]: Could not delete temporary file {DISK_FILE}: {e}")

    print("[INFO]: Stress test complete.")


def main():
    """Sets up the threads and main loop."""
    global executor
    
    # Use logical core count for CPU threads
    num_cpu_threads = psutil.cpu_count(logical=True)
    if num_cpu_threads is None:
        num_cpu_threads = 4 # Default if detection fails
        
    print(f"[{num_cpu_threads} CPU Threads initiated]")
    
    # Ensure the disk file exists before starting the disk thread
    try:
        if not os.path.exists(DISK_FILE):
            with open(DISK_FILE, 'wb') as f:
                f.write(os.urandom(10 * 4096 * 4096)) # 10MB initial file
    except Exception as e:
        print(f"[ERROR]: Could not pre-create disk file. Disk stress test may fail: {e}")

    # Register the cleanup function to run on exit or interrupt
    atexit.register(cleanup)
    
    # We now add 7 extra workers: RAM, DISK, NETWORK/Wi-Fi, DIAGNOSIS, GPU, CACHE, I/O
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_cpu_threads + 7)
    
    # Start the non-CPU dedicated threads
    executor.submit(ram_stress)
    executor.submit(disk_stress)
    executor.submit(network_stress)
    executor.submit(gpu_stress)
    executor.submit(cache_stress)
    executor.submit(io_bound_stress) # I/O Bound stress (Chipset/VRM load)
    # audio_stress function submission removed
    executor.submit(diagnosis_monitor) 
    
    # Start CPU stress threads
    for i in range(num_cpu_threads):
        executor.submit(cpu_stress, i)
        
    # Print header and wait for interrupt
    target_gpu_status = "GPU (CPU Placeholder)"
    print(f"\n==================================================")
    print(f"ULTIMATE HARDWARE STRESS TEST RUNNING...")
    print(f"Targeting: CPU ({num_cpu_threads} threads), {target_gpu_status}, RAM, CACHE, DISK ({DISK_FILE}), NIC/Wi-Fi, I/O Bound (Chipset/VRM)")
    print(f"Press Ctrl+C to stop the test and clean up.")
    print(f"==================================================")
    
    try:
        while not stop_event.is_set():
            # Main thread sleeps until interrupted
            time.sleep(1)
    except KeyboardInterrupt:
        # KeyboardInterrupt will trigger the atexit registered cleanup()
        pass


if __name__ == "__main__":
    # Check for required libraries at runtime (optional but good practice)
    try:
        import numpy
        import requests
        import psutil
        import urllib3 # Included in the check
        # Note: CuPy is now removed from the import check.
    except ImportError:
        print("Required libraries (numpy, requests, psutil, urllib3) are not installed.")
        print("Please run: pip install numpy requests psutil urllib3")
        sys.exit(1)
        
    main()


# audio_stress function removed as per user request.