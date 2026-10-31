import pytest
from unittest.mock import MagicMock, patch

from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.schemas import GPUMemorySnapshot


def test_gpu_monitor_disabled():
    monitor = GPUResourceMonitor(enabled=False)
    snap = monitor.get_memory_snapshot()
    assert snap.is_available is True
    assert snap.total_mb == 6141.0
    assert monitor.is_memory_safe(1000.0) is True


def test_gpu_monitor_nvml_success():
    monitor = GPUResourceMonitor(enabled=True)
    monitor._nvml_initialized = True
    monitor._nvml_handle = MagicMock()

    mock_mem = MagicMock()
    mock_mem.total = 6 * 1024 * 1024 * 1024  # 6144 MB
    mock_mem.used = 2 * 1024 * 1024 * 1024   # 2048 MB
    mock_mem.free = 4 * 1024 * 1024 * 1024   # 4096 MB

    mock_util = MagicMock()
    mock_util.gpu = 15

    with patch("pynvml.nvmlDeviceGetMemoryInfo", return_value=mock_mem), \
         patch("pynvml.nvmlDeviceGetTemperature", return_value=52), \
         patch("pynvml.nvmlDeviceGetUtilizationRates", return_value=mock_util):
        snap = monitor.get_memory_snapshot()
        assert snap.is_available is True
        assert snap.total_mb == 6144.0
        assert snap.used_mb == 2048.0
        assert snap.free_mb == 4096.0
        assert snap.temperature_c == 52.0
        assert snap.utilization_percent == 15.0

        # Memory safety check: 2000 MB + 2048 MB = 4048 MB <= 90% of 6144 MB (5529.6 MB)
        assert monitor.is_memory_safe(required_mb=2000.0, max_fraction=0.90) is True
        # High utilization threshold: 4000 MB + 2048 MB = 6048 MB > 5529.6 MB
        assert monitor.is_memory_safe(required_mb=4000.0, max_fraction=0.90) is False


def test_gpu_monitor_nvml_fails_falls_back_to_nvidia_smi():
    monitor = GPUResourceMonitor(enabled=True)
    monitor._nvml_initialized = False

    mock_sub = MagicMock()
    mock_sub.returncode = 0
    mock_sub.stdout = "6144, 2048, 4096, 25, 55\n"

    with patch("subprocess.run", return_value=mock_sub):
        snap = monitor.get_memory_snapshot()

    assert snap.is_available is True
    assert snap.total_mb == 6144.0
    assert snap.used_mb == 2048.0
    assert snap.free_mb == 4096.0
    assert snap.utilization_percent == 25.0
    assert snap.temperature_c == 55.0


def test_gpu_monitor_all_tools_unavailable_graceful_degradation():
    monitor = GPUResourceMonitor(enabled=True)
    monitor._nvml_initialized = False

    with patch("subprocess.run", side_effect=FileNotFoundError("nvidia-smi not found")):
        snap = monitor.get_memory_snapshot()

    assert snap.is_available is False
    assert snap.total_mb == 6141.0
    # Does not crash or raise exception
    assert monitor.is_memory_safe(1000.0) is True


def test_non_zero_residual_memory_handling():
    monitor = GPUResourceMonitor(enabled=True)
    monitor._nvml_initialized = True
    monitor._nvml_handle = MagicMock()

    mock_mem = MagicMock()
    mock_mem.total = 6144 * 1024 * 1024
    mock_mem.used = 500 * 1024 * 1024   # 500 MB residual desktop/OS allocation
    mock_mem.free = (6144 - 500) * 1024 * 1024

    mock_util = MagicMock()
    mock_util.gpu = 0

    with patch("pynvml.nvmlDeviceGetMemoryInfo", return_value=mock_mem), \
         patch("pynvml.nvmlDeviceGetTemperature", return_value=45), \
         patch("pynvml.nvmlDeviceGetUtilizationRates", return_value=mock_util):
        snap = monitor.get_memory_snapshot()
        assert snap.used_mb == 500.0
        assert snap.free_mb == 5644.0
        # Safe to load DeepSeek (~4700 MB) when 500 MB residual: 500 + 4700 = 5200 MB <= 90% (5529.6 MB)
        assert monitor.is_memory_safe(required_mb=4700.0, max_fraction=0.90) is True
