import time
import subprocess
import threading
import json
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetUtilizationRates, nvmlDeviceGetMemoryInfo, nvmlShutdown

class GPUProfiler:
    def __init__(self, gpu_index=0):
        self.gpu_index = gpu_index
        self.running = False
        self.data = {
            'timestamps': [],
            'compute_util': [],
            'mem_util': [],
            'mem_used_gb': [],
            'mem_total_gb': None
        }
        self.sample_interval = 1.0  # Sample every second

    def _monitor_loop(self):
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(self.gpu_index)
        mem_info = nvmlDeviceGetMemoryInfo(handle)
        self.data['mem_total_gb'] = mem_info.total / (1024 ** 3)  # Convert to GB

        while self.running:
            try:
                # Get GPU utilization
                utilization = nvmlDeviceGetUtilizationRates(handle)
                mem_info = nvmlDeviceGetMemoryInfo(handle)

                # Record data
                timestamp = time.time()
                self.data['timestamps'].append(timestamp)
                self.data['compute_util'].append(utilization.gpu)
                self.data['mem_util'].append(utilization.memory)
                self.data['mem_used_gb'].append(mem_info.used / (1024 ** 3))

            except Exception as e:
                print(f"Error sampling GPU data: {e}")
            time.sleep(self.sample_interval)
        nvmlShutdown()

    def start(self):
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

    def calculate_stats(self):
        if not self.data['compute_util']:
            return {}

        compute_util = self.data['compute_util']
        mem_used = self.data['mem_used_gb']
        mem_total = self.data['mem_total_gb']

        # Calculate idle time (assuming < 10% utilization is idle)
        idle_samples = sum(1 for util in compute_util if util < 10)
        total_samples = len(compute_util)
        idle_percent = (idle_samples / total_samples) * 100 if total_samples > 0 else 0

        return {
            'duration_sec': self.data['timestamps'][-1] - self.data['timestamps'][0] if self.data['timestamps'] else 0,
            'avg_compute_util': sum(compute_util) / len(compute_util),
            'avg_mem_util': sum(mem_used) / len(mem_used) / mem_total * 100 if mem_total else 0,
            'peak_mem_util_gb': max(mem_used) if mem_used else 0,
            'idle_percent': idle_percent,
            'mem_total_gb': mem_total
        }