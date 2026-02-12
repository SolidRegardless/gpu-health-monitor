#!/usr/bin/env python3
# MIT License
# Copyright (c) 2026 Stuart Hart <stuarthart@msn.com>
#
# GPU Health Monitor - Production-grade GPU monitoring and predictive maintenance
# https://github.com/stuarthart/gpu-health-monitor
#
# Multi-GPU Mock DCGM Exporter with Enhanced Telemetry
# Simulates 5 GPUs with different health profiles

import os
import time
import random
import math
from datetime import datetime
from flask import Flask, Response

app = Flask(__name__)

# Configuration
EXPORTER_PORT = int(os.getenv('EXPORTER_PORT', '9400'))
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '10'))

# GPU Profiles - Simulate different health states
GPU_PROFILES = [
    {
        'index': 0,
        'uuid': 'GPU-abc123def456',
        'model': 'NVIDIA A100-SXM4-80GB',
        'profile': 'healthy',
        'base_temp': 65.0,
        'base_power': 300.0,
        'age_months': 6,
        'ecc_error_rate': 0.001,  # Very low
        'degradation_factor': 1.0,  # No degradation
    },
    {
        'index': 1,
        'uuid': 'GPU-def456abc789',
        'model': 'NVIDIA A100-SXM4-80GB',
        'profile': 'high_temp',
        'base_temp': 72.0,  # Runs hotter
        'base_power': 310.0,
        'age_months': 18,
        'ecc_error_rate': 0.005,  # Moderate
        'degradation_factor': 0.95,  # Slight degradation
    },
    {
        'index': 2,
        'uuid': 'GPU-ghi789jkl012',
        'model': 'NVIDIA H100-SXM5-80GB',
        'profile': 'power_hungry',
        'base_temp': 68.0,
        'base_power': 340.0,  # Higher power
        'age_months': 3,
        'ecc_error_rate': 0.002,
        'degradation_factor': 1.0,
    },
    {
        'index': 3,
        'uuid': 'GPU-mno345pqr678',
        'model': 'NVIDIA A100-SXM4-80GB',
        'profile': 'aging',
        'base_temp': 70.0,
        'base_power': 295.0,
        'age_months': 36,  # 3 years old
        'ecc_error_rate': 0.02,  # Higher ECC errors
        'degradation_factor': 0.85,  # Notable degradation
    },
    {
        'index': 4,
        'uuid': 'GPU-stu901vwx234',
        'model': 'NVIDIA H100-SXM5-80GB',
        'profile': 'excellent',
        'base_temp': 62.0,  # Runs cool
        'base_power': 290.0,
        'age_months': 1,  # New
        'ecc_error_rate': 0.0001,  # Minimal errors
        'degradation_factor': 1.0,
    },
]


class GPUSimulator:
    """Simulate a single GPU with realistic behavior patterns."""
    
    def __init__(self, profile):
        self.profile = profile
        self.start_time = time.time()
        
        # Counters
        self.ecc_sbe_aggregate = 0
        self.ecc_dbe_aggregate = 0
        self.total_energy_consumed = 0  # mJ
        self.pcie_tx_bytes = 0
        self.pcie_rx_bytes = 0
        
        # NVLink counters
        self.nvlink_rx_bytes = [0] * 12  # 12 NVLink connections on A100/H100
        self.nvlink_tx_bytes = [0] * 12
        
        # Fan speed target (%)
        self.fan_speed_target = 50.0
        
        # Initialize with some history for aging GPUs
        if self.profile['age_months'] > 12:
            self.ecc_sbe_aggregate = random.randint(100, 500)
            if self.profile['age_months'] > 24:
                self.ecc_dbe_aggregate = random.randint(1, 5)
    
    def get_current_time_seconds(self):
        """Get time since start in seconds."""
        return time.time() - self.start_time
    
    def get_workload_intensity(self):
        """
        Simulate varying workload intensity.
        Different GPUs have different usage patterns.
        """
        t = self.get_current_time_seconds()
        
        if self.profile['profile'] == 'excellent':
            # Steady high utilization
            return 0.85 + 0.1 * math.sin(t * 0.1)
        elif self.profile['profile'] == 'aging':
            # Lower utilization (assigned lighter workloads)
            return 0.4 + 0.2 * math.sin(t * 0.05)
        else:
            # Normal 5-minute cycle
            cycle_time = 300.0
            phase = (t % cycle_time) / cycle_time
            
            if phase < 0.2:
                return 0.1
            elif phase < 0.3:
                return (phase - 0.2) / 0.1 * 0.9 + 0.1
            elif phase < 0.7:
                return 0.9 + 0.1 * math.sin(t * 0.5)
            elif phase < 0.8:
                return 1.0 - ((phase - 0.7) / 0.1 * 0.9)
            else:
                return 0.1
    
    def get_temperature(self):
        """GPU temperature based on workload and profile."""
        intensity = self.get_workload_intensity()
        base = self.profile['base_temp']
        
        # Aging GPUs run hotter
        age_factor = 1.0 + (self.profile['age_months'] / 12) * 0.1
        
        temp = base * age_factor + (intensity * 15.0) + random.gauss(0, 1.5)
        
        # Occasional spikes
        if random.random() < 0.01:
            temp += random.uniform(5, 10)
        
        return max(30, min(95, temp))
    
    def get_memory_temperature(self):
        """Memory temperature (typically 5-10°C higher than GPU)."""
        gpu_temp = self.get_temperature()
        offset = random.uniform(5, 10)
        
        # Aging memory runs even hotter
        if self.profile['age_months'] > 24:
            offset += 3
        
        return max(35, min(105, gpu_temp + offset))
    
    def get_power_usage(self):
        """Power usage based on workload and efficiency."""
        intensity = self.get_workload_intensity()
        base = self.profile['base_power']
        degradation = self.profile['degradation_factor']
        
        # Degraded GPUs are less power-efficient
        efficiency_factor = 1.0 / degradation
        
        power = (base + (intensity * 100.0)) * efficiency_factor + random.gauss(0, 5)
        
        # Update energy counter (mJ)
        dt = POLL_INTERVAL  # seconds
        self.total_energy_consumed += int(power * dt * 1000)
        
        return max(50, min(700 if 'H100' in self.profile['model'] else 400, power))
    
    def get_fan_speed(self):
        """Fan speed based on temperature."""
        temp = self.get_temperature()
        
        # Simple fan curve
        if temp < 60:
            target = 30
        elif temp < 70:
            target = 40 + (temp - 60) * 3
        elif temp < 80:
            target = 70 + (temp - 70) * 2
        else:
            target = min(100, 90 + (temp - 80))
        
        # Gradual approach to target
        self.fan_speed_target += (target - self.fan_speed_target) * 0.3
        
        return max(0, min(100, self.fan_speed_target + random.gauss(0, 2)))
    
    def get_nvlink_bandwidth(self):
        """Simulate NVLink traffic (if GPUs are peer-connected)."""
        intensity = self.get_workload_intensity()
        
        # Only some GPUs use NVLink heavily
        if intensity > 0.7 and self.profile['index'] in [0, 1, 2]:
            # Active NVLink traffic
            for i in range(12):
                if i < 6:  # First 6 links active
                    bytes_per_sec = random.uniform(10e9, 25e9)  # 10-25 GB/s
                    self.nvlink_rx_bytes[i] += int(bytes_per_sec * POLL_INTERVAL)
                    self.nvlink_tx_bytes[i] += int(bytes_per_sec * POLL_INTERVAL)
        
        return self.nvlink_rx_bytes, self.nvlink_tx_bytes
    
    def get_ecc_errors(self):
        """ECC errors based on age and error rate."""
        t = self.get_current_time_seconds()
        
        # Volatile counters
        sbe_volatile = int((t % 3600) / 360 * self.profile['ecc_error_rate'] * 100)
        dbe_volatile = 1 if random.random() < self.profile['ecc_error_rate'] / 10 else 0
        
        # Aggregate counters
        if random.random() < self.profile['ecc_error_rate']:
            self.ecc_sbe_aggregate += random.randint(1, 5)
        
        if random.random() < self.profile['ecc_error_rate'] / 100:
            self.ecc_dbe_aggregate += 1
        
        return {
            'sbe_volatile': sbe_volatile,
            'dbe_volatile': dbe_volatile,
            'sbe_aggregate': self.ecc_sbe_aggregate,
            'dbe_aggregate': self.ecc_dbe_aggregate,
        }
    
    def get_memory_usage(self):
        """Memory usage (80GB A100/H100)."""
        intensity = self.get_workload_intensity()
        total_mb = 81920
        
        # Different workload types use different amounts of memory
        if self.profile['profile'] == 'excellent':
            used_mb = int(total_mb * 0.9)  # Fully utilized
        elif self.profile['profile'] == 'aging':
            used_mb = int(total_mb * 0.3)  # Light workloads
        else:
            used_mb = int(total_mb * (0.1 + intensity * 0.7))
        
        return {
            'total': total_mb,
            'used': used_mb,
            'free': total_mb - used_mb,
            'util_pct': (used_mb / total_mb) * 100
        }
    
    def get_performance_metrics(self):
        """Performance metrics adjusted for degradation."""
        intensity = self.get_workload_intensity()
        degradation = self.profile['degradation_factor']
        
        return {
            'sm_active': intensity * 100 * degradation,
            'sm_occupancy': intensity * 50 * degradation,
            'tensor_active': (intensity * 90 if intensity > 0.5 else 0) * degradation,
            'dram_active': intensity * 70,
            'pcie_tx_mbps': random.uniform(100, 500) if intensity > 0.3 else random.uniform(10, 50),
            'pcie_rx_mbps': random.uniform(2000, 5000) if intensity > 0.3 else random.uniform(100, 500),
        }
    
    def get_clock_frequencies(self):
        """Clock frequencies."""
        intensity = self.get_workload_intensity()
        
        if 'H100' in self.profile['model']:
            base_sm = 1230
            boost_sm = 1830
        else:  # A100
            base_sm = 1095
            boost_sm = 1410
        
        sm_clock = int(base_sm + (boost_sm - base_sm) * intensity * self.profile['degradation_factor'])
        mem_clock = 1593  # HBM2e fixed
        
        return {'sm_clock_mhz': sm_clock, 'mem_clock_mhz': mem_clock}
    
    def get_throttle_reasons(self):
        """Throttle reasons based on temp/power."""
        temp = self.get_temperature()
        power = self.get_power_usage()
        
        throttle = 0
        
        if temp > 85:
            throttle |= (1 << 6)
        if power > 380:
            throttle |= (1 << 7)
        if random.random() < 0.1:
            throttle |= (1 << 2)
        
        return throttle


# Global simulators
simulators = [GPUSimulator(profile) for profile in GPU_PROFILES]


def generate_prometheus_metrics():
    """Generate metrics for all GPUs in Prometheus format."""
    timestamp_ms = int(time.time() * 1000)
    metrics = []
    
    for sim in simulators:
        gpu = sim.profile
        
        # Get all metrics
        temp = sim.get_temperature()
        mem_temp = sim.get_memory_temperature()
        power = sim.get_power_usage()
        fan_speed = sim.get_fan_speed()
        throttle = sim.get_throttle_reasons()
        ecc = sim.get_ecc_errors()
        memory = sim.get_memory_usage()
        perf = sim.get_performance_metrics()
        clocks = sim.get_clock_frequencies()
        nvlink_rx, nvlink_tx = sim.get_nvlink_bandwidth()
        
        gpu_idx = gpu['index']
        uuid = gpu['uuid']
        model = gpu['model']
        
        # Helper to add metric
        def add_metric(name, value):
            metrics.append(f'{name}{{gpu="{gpu_idx}",UUID="{uuid}",modelName="{model}"}} {value} {timestamp_ms}')
        
        # Core metrics
        add_metric('DCGM_FI_DEV_GPU_TEMP', f'{temp:.1f}')
        add_metric('DCGM_FI_DEV_MEMORY_TEMP', f'{mem_temp:.1f}')
        add_metric('DCGM_FI_DEV_POWER_USAGE', f'{power:.1f}')
        add_metric('DCGM_FI_DEV_TOTAL_ENERGY_CONSUMPTION', sim.total_energy_consumed)
        add_metric('DCGM_FI_DEV_FAN_SPEED', f'{fan_speed:.0f}')
        
        # Throttle
        add_metric('DCGM_FI_DEV_CLOCK_THROTTLE_REASONS', throttle)
        
        # Memory
        add_metric('DCGM_FI_DEV_FB_FREE', memory['free'])
        add_metric('DCGM_FI_DEV_FB_USED', memory['used'])
        add_metric('DCGM_FI_DEV_FB_TOTAL', memory['total'])
        
        # ECC
        add_metric('DCGM_FI_DEV_ECC_SBE_VOL_TOTAL', ecc['sbe_volatile'])
        add_metric('DCGM_FI_DEV_ECC_DBE_VOL_TOTAL', ecc['dbe_volatile'])
        add_metric('DCGM_FI_DEV_ECC_SBE_AGG_TOTAL', ecc['sbe_aggregate'])
        add_metric('DCGM_FI_DEV_ECC_DBE_AGG_TOTAL', ecc['dbe_aggregate'])
        
        # Performance
        add_metric('DCGM_FI_PROF_SM_ACTIVE', f'{perf["sm_active"]:.1f}')
        add_metric('DCGM_FI_PROF_SM_OCCUPANCY', f'{perf["sm_occupancy"]:.1f}')
        add_metric('DCGM_FI_PROF_PIPE_TENSOR_ACTIVE', f'{perf["tensor_active"]:.1f}')
        add_metric('DCGM_FI_PROF_DRAM_ACTIVE', f'{perf["dram_active"]:.1f}')
        add_metric('DCGM_FI_PROF_PCIE_TX_BYTES', f'{int(perf["pcie_tx_mbps"] * 1024 * 1024)}')
        add_metric('DCGM_FI_PROF_PCIE_RX_BYTES', f'{int(perf["pcie_rx_mbps"] * 1024 * 1024)}')
        
        # Clocks
        add_metric('DCGM_FI_DEV_SM_CLOCK', clocks['sm_clock_mhz'])
        add_metric('DCGM_FI_DEV_MEM_CLOCK', clocks['mem_clock_mhz'])
        
        # Utilization
        add_metric('DCGM_FI_DEV_GPU_UTIL', f'{perf["sm_active"]:.1f}')
        add_metric('DCGM_FI_DEV_MEM_COPY_UTIL', f'{perf["dram_active"] * 0.8:.1f}')
        
        # NVLink bandwidth (total across all links)
        total_nvlink_rx = sum(nvlink_rx[:6]) / POLL_INTERVAL  # bytes/sec
        total_nvlink_tx = sum(nvlink_tx[:6]) / POLL_INTERVAL
        add_metric('DCGM_FI_PROF_NVLINK_RX_BYTES', int(total_nvlink_rx))
        add_metric('DCGM_FI_PROF_NVLINK_TX_BYTES', int(total_nvlink_tx))
    
    return '\n'.join(metrics) + '\n'


@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint."""
    metrics_text = generate_prometheus_metrics()
    return Response(metrics_text, mimetype='text/plain')


@app.route('/health')
def health():
    """Health check endpoint."""
    return {
        'status': 'healthy',
        'gpu_count': len(simulators),
        'gpus': [{'index': s.profile['index'], 'uuid': s.profile['uuid'], 'profile': s.profile['profile']} for s in simulators],
        'uptime_seconds': simulators[0].get_current_time_seconds()
    }


if __name__ == '__main__':
    print("=" * 80)
    print("Multi-GPU Mock DCGM Exporter")
    print("=" * 80)
    print(f"Simulating {len(GPU_PROFILES)} GPUs with different health profiles:")
    for profile in GPU_PROFILES:
        print(f"  GPU {profile['index']}: {profile['uuid']} ({profile['profile']}) - {profile['model']}")
    print(f"\nMetrics endpoint: http://0.0.0.0:{EXPORTER_PORT}/metrics")
    print(f"Health endpoint: http://0.0.0.0:{EXPORTER_PORT}/health")
    print(f"Poll interval: {POLL_INTERVAL}s")
    print("=" * 80)
    
    app.run(host='0.0.0.0', port=EXPORTER_PORT, debug=False)
