import logging
import subprocess
import time
from typing import Optional
from app.ai.schemas import GPUMemorySnapshot
from app.core.config import settings

logger = logging.getLogger(__name__)


class GPUResourceMonitor:
    """
    Monitors GPU memory, utilization, and temperature using:
    1. NVIDIA NVML (pynvml) as primary high-performance API.
    2. nvidia-smi CLI as secondary fallback.
    3. Graceful fallback if neither is available.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._nvml_initialized = False
        self._nvml_handle = None

        if self.enabled:
            self._try_init_nvml()

    def _try_init_nvml(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            if pynvml.nvmlDeviceGetCount() > 0:
                self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                self._nvml_initialized = True
                logger.info("GPUResourceMonitor initialized via NVML.")
        except Exception as e:
            logger.warning(f"NVML initialization failed: {e}. Falling back to nvidia-smi.")
            self._nvml_initialized = False
            self._nvml_handle = None

    def get_memory_snapshot(self) -> GPUMemorySnapshot:
        """Returns the current GPU memory and health metrics."""
        if not self.enabled:
            return GPUMemorySnapshot(
                total_mb=6141.0,
                used_mb=0.0,
                free_mb=6141.0,
                utilization_percent=0.0,
                temperature_c=45.0,
                is_available=True,
                timestamp=time.time(),
            )

        # 1. Primary: NVML
        if self._nvml_initialized and self._nvml_handle:
            try:
                import pynvml
                mem = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                temp = pynvml.nvmlDeviceGetTemperature(self._nvml_handle, pynvml.NVML_TEMPERATURE_GPU)
                util = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
                total_mb = mem.total / (1024.0 * 1024.0)
                used_mb = mem.used / (1024.0 * 1024.0)
                free_mb = mem.free / (1024.0 * 1024.0)
                return GPUMemorySnapshot(
                    total_mb=round(total_mb, 1),
                    used_mb=round(used_mb, 1),
                    free_mb=round(free_mb, 1),
                    utilization_percent=float(util.gpu),
                    temperature_c=float(temp),
                    is_available=True,
                    timestamp=time.time(),
                )
            except Exception as e:
                logger.warning(f"NVML query failed: {e}. Attempting nvidia-smi fallback.")

        # 2. Secondary: nvidia-smi CLI
        return self._query_nvidia_smi()

    def _query_nvidia_smi(self) -> GPUMemorySnapshot:
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                parts = [p.strip() for p in result.stdout.strip().split(",")]
                if len(parts) >= 5:
                    total_mb = float(parts[0])
                    used_mb = float(parts[1])
                    free_mb = float(parts[2])
                    util = float(parts[3])
                    temp = float(parts[4])
                    return GPUMemorySnapshot(
                        total_mb=total_mb,
                        used_mb=used_mb,
                        free_mb=free_mb,
                        utilization_percent=util,
                        temperature_c=temp,
                        is_available=True,
                        timestamp=time.time(),
                    )
        except Exception as e:
            logger.warning(f"nvidia-smi query failed: {e}.")

        # 3. Graceful fallback (degraded mode)
        return GPUMemorySnapshot(
            total_mb=6141.0,
            used_mb=0.0,
            free_mb=6141.0,
            utilization_percent=0.0,
            temperature_c=None,
            is_available=False,
            timestamp=time.time(),
        )

    def is_memory_safe(self, required_mb: float = 2000.0, max_fraction: Optional[float] = None) -> bool:
        """
        Validates whether sufficient VRAM headroom exists without breaching safety thresholds.
        """
        fraction = max_fraction or settings.GPU_MAX_MEMORY_FRACTION
        snap = self.get_memory_snapshot()
        if not snap.is_available:
            # If monitoring is unavailable, assume safe to operate unless strictly prevented
            return True

        allowed_used_mb = snap.total_mb * fraction
        projected_used_mb = snap.used_mb + required_mb
        return projected_used_mb <= allowed_used_mb
