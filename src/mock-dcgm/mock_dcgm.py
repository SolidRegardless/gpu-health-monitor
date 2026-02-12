#!/usr/bin/env python3
# MIT License
# Copyright (c) 2026 Stuart Hart <stuarthart@msn.com>
#
# GPU Health Monitor - Production-grade GPU monitoring and predictive maintenance
# https://github.com/stuarthart/gpu-health-monitor
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""
Mock DCGM Exporter
Simulates NVIDIA DCGM metrics in Prometheus format for testing.
"""

import os
import time
import random
import math
from datetime import datetime
from flask import Flask, Response

app = Flask(__name__)

# Configuration
GPU_UUID = os.getenv('GPU_UUID', 'GPU-abc123def456')
GPU_MODEL = os.getenv('GPU_MODEL', 'NVIDIA A100-SXM4-80GB')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '10'))
EXPORTER_PORT = int(os.getenv('EXPORTER_PORT', '9400'))

# Simulation state
class GPUSimulator:
    def __init__(self):
        self.start_time = time.time()
        self.base_temp = 65.0
        self.base_power = 300.0
        self.base_mem_temp = 70.0
        
        # Counter for aggregate ECC errors (monotonically increasing)
        self.ecc_sbe_aggregate = 0
        self.ecc_dbe_aggregate = 0
        
        # Simulation of workload patterns
        self.workload_phase = 0
        
    def get_current_time_seconds(self):
        """Get time since start in seconds."""
        return time.time() - self.start_time
    
    def get_workload_intensity(self):
        """
        Simulate varying workload intensity over time.
        Creates a pattern: idle → ramp-up → peak → ramp-down → idle
        """
        t = self.get_current_time_seconds()
        
        # 5-minute cycle
        cycle_time = 300.0
        phase = (t % cycle_time) / cycle_time
        
        if phase < 0.2:  # Idle
            return 0.1
        elif phase < 0.3:  # Ramp-up
            return (phase - 0.2) / 0.1 * 0.9 + 0.1
        elif phase < 0.7:  # Peak workload
            return 0.9 + 0.1 * math.sin(t * 0.5)  # Small oscillation
        elif phase < 0.8:  # Ramp-down
            return 1.0 - ((phase - 0.7) / 0.1 * 0.9)
        else:  # Idle
            return 0.1
    
    def get_temperature(self):
        """Simulate GPU temperature based on workload."""
        intensity = self.get_workload_intensity()
        
        # Base temp + workload heating + random variation
        temp = self.base_temp + (intensity * 15.0) + random.gauss(0, 1.5)
        
        # Add occasional spike (1% chance)
        if random.random() < 0.01:
            temp += random.uniform(5, 10)
        
        return max(30, min(95, temp))
    
    def get_memory_temperature(self):
        """Simulate memory temperature (typically higher than GPU)."""
        gpu_temp = self.get_temperature()
        mem_temp = gpu_temp + random.uniform(3, 8)
        return max(35, min(100, mem_temp))
    
    def get_power_usage(self):
        """Simulate power usage based on workload."""
        intensity = self.get_workload_intensity()
        
        # Base power + workload power + random variation
        power = self.base_power + (intensity * 100.0) + random.gauss(0, 5)
        
        return max(50, min(400, power))
    
    def get_throttle_reasons(self):
        """
        Simulate throttle reasons bitmask.
        Occasionally trigger thermal or power throttling.
        """
        temp = self.get_temperature()
        power = self.get_power_usage()
        
        throttle = 0
        
        # Thermal throttling if temp > 85°C
        if temp > 85:
            throttle |= (1 << 6)  # HW_THERMAL
        
        # Power throttling if power > 380W
        if power > 380:
            throttle |= (1 << 7)  # HW_POWER_BRAKE
        
        # Software power cap (occasionally)
        if random.random() < 0.1:
            throttle |= (1 << 2)  # SW_POWER_CAP
        
        return throttle
    
    def get_ecc_errors(self):
        """
        Simulate ECC errors.
        SBE: Occasional single-bit errors (correctable)
        DBE: Very rare double-bit errors (uncorrectable)
        """
        # Volatile counters (reset periodically)
        t = self.get_current_time_seconds()
        sbe_volatile = int((t % 3600) / 360)  # Increment every 6 minutes
        dbe_volatile = 1 if random.random() < 0.0001 else 0  # Very rare
        
        # Aggregate counters (monotonic)
        # Occasional ECC error events
        if random.random() < 0.01:  # 1% chance per poll
            self.ecc_sbe_aggregate += random.randint(1, 5)
        
        if random.random() < 0.0001:  # 0.01% chance per poll
            self.ecc_dbe_aggregate += 1
        
        return {
            'sbe_volatile': sbe_volatile,
            'dbe_volatile': dbe_volatile,
            'sbe_aggregate': self.ecc_sbe_aggregate,
            'dbe_aggregate': self.ecc_dbe_aggregate,
        }
    
    def get_memory_usage(self):
        """Simulate memory usage (80GB A100)."""
        intensity = self.get_workload_intensity()
        
        total_mb = 81920  # 80 GB
        used_mb = int(total_mb * (0.1 + intensity * 0.8))  # 10-90% usage
        free_mb = total_mb - used_mb
        
        return {
            'total': total_mb,
            'used': used_mb,
            'free': free_mb,
            'util_pct': (used_mb / total_mb) * 100
        }
    
    def get_performance_metrics(self):
        """Simulate performance metrics."""
        intensity = self.get_workload_intensity()
        
        return {
            'sm_active': intensity * 100,  # 0-100%
            'sm_occupancy': intensity * 50,  # 0-50% (typical)
            'tensor_active': intensity * 90 if intensity > 0.5 else 0,  # Tensor cores active during ML
            'dram_active': intensity * 70,  # Memory bandwidth usage
            'pcie_tx_mbps': random.uniform(100, 500) if intensity > 0.3 else random.uniform(10, 50),
            'pcie_rx_mbps': random.uniform(2000, 5000) if intensity > 0.3 else random.uniform(100, 500),
        }
    
    def get_clock_frequencies(self):
        """Simulate clock frequencies."""
        intensity = self.get_workload_intensity()
        
        # A100 typical clocks
        base_sm_clock = 1095  # MHz
        boost_sm_clock = 1410  # MHz
        
        sm_clock = int(base_sm_clock + (boost_sm_clock - base_sm_clock) * intensity)
        mem_clock = 1593  # HBM2e runs at fixed frequency
        
        return {
            'sm_clock_mhz': sm_clock,
            'mem_clock_mhz': mem_clock
        }


# Global simulator instance
simulator = GPUSimulator()


def generate_prometheus_metrics():
    """Generate metrics in Prometheus format."""
    timestamp_ms = int(time.time() * 1000)
    
    # Get simulated values
    temp = simulator.get_temperature()
    mem_temp = simulator.get_memory_temperature()
    power = simulator.get_power_usage()
    throttle = simulator.get_throttle_reasons()
    ecc = simulator.get_ecc_errors()
    memory = simulator.get_memory_usage()
    perf = simulator.get_performance_metrics()
    clocks = simulator.get_clock_frequencies()
    
    # Retired pages (simulated - very rare)
    retired_sbe = random.randint(0, 2) if random.random() < 0.001 else 0
    retired_dbe = 1 if ecc['dbe_aggregate'] > 10 else 0
    
    metrics = []
    
    # Helper function to add metric
    def add_metric(name, value, help_text=None, metric_type='gauge'):
        if help_text:
            metrics.append(f'# HELP {name} {help_text}')
            metrics.append(f'# TYPE {name} {metric_type}')
        metrics.append(f'{name}{{gpu="0",UUID="{GPU_UUID}",modelName="{GPU_MODEL}"}} {value} {timestamp_ms}')
    
    # Temperature metrics
    add_metric('DCGM_FI_DEV_GPU_TEMP', f'{temp:.1f}', 'GPU temperature (C)', 'gauge')
    add_metric('DCGM_FI_DEV_MEMORY_TEMP', f'{mem_temp:.1f}', 'Memory temperature (C)', 'gauge')
    
    # Power metrics
    add_metric('DCGM_FI_DEV_POWER_USAGE', f'{power:.1f}', 'Power usage (W)', 'gauge')
    add_metric('DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION', f'{int(simulator.get_current_time_seconds() * power * 1000)}', 
               'Total energy consumption (mJ)', 'counter')
    
    # Throttle reasons
    add_metric('DCGM_FI_DEV_CLOCK_THROTTLE_REASONS', throttle, 'Clock throttle reasons bitmask', 'gauge')
    
    # Memory metrics
    add_metric('DCGM_FI_DEV_FB_FREE', memory['free'], 'Framebuffer free (MiB)', 'gauge')
    add_metric('DCGM_FI_DEV_FB_USED', memory['used'], 'Framebuffer used (MiB)', 'gauge')
    
    # ECC errors
    add_metric('DCGM_FI_DEV_ECC_SBE_VOL_TOTAL', ecc['sbe_volatile'], 'Single-bit ECC errors (volatile)', 'counter')
    add_metric('DCGM_FI_DEV_ECC_DBE_VOL_TOTAL', ecc['dbe_volatile'], 'Double-bit ECC errors (volatile)', 'counter')
    add_metric('DCGM_FI_DEV_ECC_SBE_AGG_TOTAL', ecc['sbe_aggregate'], 'Single-bit ECC errors (aggregate)', 'counter')
    add_metric('DCGM_FI_DEV_ECC_DBE_AGG_TOTAL', ecc['dbe_aggregate'], 'Double-bit ECC errors (aggregate)', 'counter')
    add_metric('DCGM_FI_DEV_RETIRED_SBE', retired_sbe, 'Retired pages due to SBE', 'gauge')
    add_metric('DCGM_FI_DEV_RETIRED_DBE', retired_dbe, 'Retired pages due to DBE', 'gauge')
    
    # Performance metrics
    add_metric('DCGM_FI_PROF_SM_ACTIVE', f'{perf["sm_active"]:.1f}', 'SM active (%)', 'gauge')
    add_metric('DCGM_FI_PROF_SM_OCCUPANCY', f'{perf["sm_occupancy"]:.1f}', 'SM occupancy (%)', 'gauge')
    add_metric('DCGM_FI_PROF_PIPE_TENSOR_ACTIVE', f'{perf["tensor_active"]:.1f}', 'Tensor core active (%)', 'gauge')
    add_metric('DCGM_FI_PROF_DRAM_ACTIVE', f'{perf["dram_active"]:.1f}', 'DRAM active (%)', 'gauge')
    add_metric('DCGM_FI_PROF_PCIE_TX_BYTES', f'{int(perf["pcie_tx_mbps"] * 1024 * 1024)}', 'PCIe TX (bytes/s)', 'counter')
    add_metric('DCGM_FI_PROF_PCIE_RX_BYTES', f'{int(perf["pcie_rx_mbps"] * 1024 * 1024)}', 'PCIe RX (bytes/s)', 'counter')
    
    # Clock metrics
    add_metric('DCGM_FI_DEV_SM_CLOCK', clocks['sm_clock_mhz'], 'SM clock (MHz)', 'gauge')
    add_metric('DCGM_FI_DEV_MEM_CLOCK', clocks['mem_clock_mhz'], 'Memory clock (MHz)', 'gauge')
    
    # GPU utilization
    add_metric('DCGM_FI_DEV_GPU_UTIL', f'{perf["sm_active"]:.1f}', 'GPU utilization (%)', 'gauge')
    add_metric('DCGM_FI_DEV_MEM_COPY_UTIL', f'{perf["dram_active"] * 0.8:.1f}', 'Memory copy utilization (%)', 'gauge')
    
    return '\n'.join(metrics) + '\n'


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    metrics_text = generate_prometheus_metrics()
    return Response(metrics_text, mimetype='text/plain')


@app.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'healthy', 'gpu_uuid': GPU_UUID, 'uptime_seconds': simulator.get_current_time_seconds()}


if __name__ == '__main__':
    print(f"Mock DCGM Exporter starting...")
    print(f"GPU UUID: {GPU_UUID}")
    print(f"GPU Model: {GPU_MODEL}")
    print(f"Metrics endpoint: http://0.0.0.0:{EXPORTER_PORT}/metrics")
    print(f"Poll interval: {POLL_INTERVAL}s")
    
    app.run(host='0.0.0.0', port=EXPORTER_PORT, debug=False)
