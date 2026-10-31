import asyncio
import contextlib
import logging
import os
import tempfile
import time
from typing import Any, Callable, Dict, Optional

from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.providers.base import BaseLLMProvider, ModelLoadError, ModelUnloadError
from app.ai.schemas import ExecutionState, GPUExecutionStatus, GPUMemorySnapshot
from app.core.config import settings

logger = logging.getLogger(__name__)


class GPUExecutionError(Exception):
    """Raised when a GPU execution or state transition failure occurs."""
    pass


class InvalidStateTransitionError(GPUExecutionError):
    """Raised when an illegal state machine transition is attempted."""
    pass


class CrossProcessLock:
    """
    File-based cross-process lock using an OS-level lockfile.
    Provides multi-process execution protection for future multi-worker deployments.
    """

    def __init__(self, lockfile_path: Optional[str] = None):
        self.lockfile_path = lockfile_path or os.path.join(tempfile.gettempdir(), "adaptive_learning_gpu.lock")
        self._fd = None

    def acquire(self, timeout: float = 180.0) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # O_CREAT | O_EXCL provides atomic file creation
                self._fd = os.open(self.lockfile_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                return True
            except FileExistsError:
                time.sleep(0.05)
            except Exception as e:
                logger.warning(f"CrossProcessLock acquire warning: {e}")
                time.sleep(0.05)
        return False

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
        if os.path.exists(self.lockfile_path):
            try:
                os.unlink(self.lockfile_path)
            except Exception:
                pass

    @contextlib.contextmanager
    def lock(self, timeout: float = 180.0):
        acquired = self.acquire(timeout=timeout)
        if not acquired:
            raise GPUExecutionError("Failed to acquire cross-process GPU execution lock within timeout.")
        try:
            yield
        finally:
            self.release()


class GPUExecutionManager:
    """
    Centralized GPU Execution Manager.
    Guarantees strict sequential execution of DeepSeek and Llama on an NVIDIA RTX 4050 (6 GB VRAM).
    Enforces a strict finite state machine, request queuing, timeouts, and safe recovery.
    """

    VALID_TRANSITIONS = {
        ExecutionState.IDLE: {
            ExecutionState.DEEPSEEK_LOADING,
            ExecutionState.DEEPSEEK_ACTIVE,  # When prewarmed model is reused
            ExecutionState.LLAMA_LOADING,
            ExecutionState.ERROR,
        },
        ExecutionState.DEEPSEEK_LOADING: {
            ExecutionState.DEEPSEEK_ACTIVE,
            ExecutionState.ERROR,
        },
        ExecutionState.DEEPSEEK_ACTIVE: {
            ExecutionState.DEEPSEEK_UNLOADING,
            ExecutionState.ERROR,
        },
        ExecutionState.DEEPSEEK_UNLOADING: {
            ExecutionState.LLAMA_LOADING,
            ExecutionState.IDLE,
            ExecutionState.ERROR,
        },
        ExecutionState.LLAMA_LOADING: {
            ExecutionState.LLAMA_ACTIVE,
            ExecutionState.ERROR,
        },
        ExecutionState.LLAMA_ACTIVE: {
            ExecutionState.LLAMA_UNLOADING,
            ExecutionState.ERROR,
        },
        ExecutionState.LLAMA_UNLOADING: {
            ExecutionState.DEEPSEEK_PREWARMING,
            ExecutionState.IDLE,
            ExecutionState.ERROR,
        },
        ExecutionState.DEEPSEEK_PREWARMING: {
            ExecutionState.IDLE,
            ExecutionState.ERROR,
        },
        ExecutionState.ERROR: {
            ExecutionState.IDLE,
        },
    }

    def __init__(
        self,
        deepseek_provider: BaseLLMProvider,
        llama_provider: BaseLLMProvider,
        monitor: Optional[GPUResourceMonitor] = None,
        prewarm_mode: Optional[str] = None,
    ):
        self.deepseek = deepseek_provider
        self.llama = llama_provider
        self.monitor = monitor or GPUResourceMonitor(enabled=settings.GPU_MONITORING_ENABLED)
        self.prewarm_mode = prewarm_mode or settings.GPU_PREWARM_MODE

        self._state = ExecutionState.IDLE
        self._active_model: Optional[str] = None
        self._prewarmed_model: Optional[str] = None
        self._mutex = asyncio.Lock()
        self._current_owner_task: Optional[asyncio.Task] = None
        self._lock_depth = 0
        self._queue_counter = 0
        self._last_transition_time = time.time()
        self._cross_process_lock = CrossProcessLock()

    @property
    def state(self) -> ExecutionState:
        return self._state

    @property
    def active_model(self) -> Optional[str]:
        return self._active_model

    @property
    def prewarmed_model(self) -> Optional[str]:
        return self._prewarmed_model

    def get_status(self) -> GPUExecutionStatus:
        """Returns the current state machine and GPU status."""
        snapshot = self.monitor.get_memory_snapshot()
        return GPUExecutionStatus(
            state=self._state,
            active_model=self._active_model,
            queue_size=self._queue_counter,
            last_transition_time=self._last_transition_time,
            prewarmed_model=self._prewarmed_model,
            mode=settings.GPU_EXECUTION_MODE,
            prewarm_mode=self.prewarm_mode,
            gpu_snapshot=snapshot,
        )

    def _transition_to(self, new_state: ExecutionState, active_model: Optional[str] = None) -> None:
        """Enforces legal state transitions according to the state machine."""
        allowed = self.VALID_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            err = (
                f"Illegal state transition requested: {self._state.value} -> {new_state.value}. "
                f"Allowed transitions from {self._state.value}: {[s.value for s in allowed]}"
            )
            logger.error(err)
            self._state = ExecutionState.ERROR
            raise InvalidStateTransitionError(err)

        logger.info(f"GPU State Transition: {self._state.value} -> {new_state.value} (model={active_model})")
        self._state = new_state
        self._active_model = active_model
        self._last_transition_time = time.time()

    async def attempt_recovery(self) -> bool:
        """
        Controlled recovery mechanism:
        Force-unloads any loaded model from both LM Studio and Ollama, verifies GPU state,
        and transitions state back to IDLE.
        """
        logger.warning("Initiating controlled GPU recovery...")
        try:
            try:
                await self.deepseek.unload_model()
            except Exception as e:
                logger.warning(f"Recovery DeepSeek unload warning: {e}")

            try:
                await self.llama.unload_model()
            except Exception as e:
                logger.warning(f"Recovery Llama unload warning: {e}")

            self._active_model = None
            self._prewarmed_model = None
            self._state = ExecutionState.IDLE
            logger.info("GPU recovery completed successfully. State reset to IDLE.")
            return True
        except Exception as e:
            logger.critical(f"GPU recovery failed: {e}")
            self._state = ExecutionState.ERROR
            return False

    @contextlib.asynccontextmanager
    async def acquire_gpu(self, timeout: float = 180.0):
        """
        Queues the incoming request, acquires the mutex, and guarantees resource cleanup on exit.
        Supports task-level reentrancy so an orchestration flow holding the GPU turn lock
        can invoke sub-tasks without deadlocking.
        """
        current_task = asyncio.current_task()
        if self._current_owner_task is not None and self._current_owner_task == current_task:
            self._lock_depth += 1
            try:
                yield
            finally:
                self._lock_depth -= 1
            return

        self._queue_counter += 1
        acquired = False
        try:
            # Acquire asyncio lock with timeout
            try:
                await asyncio.wait_for(self._mutex.acquire(), timeout=timeout)
                acquired = True
                self._current_owner_task = current_task
                self._lock_depth = 1
            except asyncio.TimeoutError:
                raise GPUExecutionError(f"Timed out waiting for GPU mutex after {timeout}s.")

            # Cross-process lock for multi-process safety
            with self._cross_process_lock.lock(timeout=timeout):
                yield
        finally:
            if acquired:
                self._current_owner_task = None
                self._lock_depth = 0
                self._mutex.release()
            self._queue_counter = max(0, self._queue_counter - 1)

    async def execute_deepseek(
        self,
        reasoning_task: Callable[[], Any],
        context_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes DeepSeek inference under GPU lock protection:
        1. Acquire GPU lock
        2. Ensure clean initial state (recover if needed)
        3. Load DeepSeek (or reuse prewarmed instance)
        4. Run reasoning_task
        5. Unload DeepSeek and verify memory cleanup
        6. Transition back to IDLE
        """
        metrics = {
            "deepseek_load_ms": 0.0,
            "deepseek_inference_ms": 0.0,
            "deepseek_unload_ms": 0.0,
            "peak_vram_mb": 0.0,
        }
        async with self.acquire_gpu(timeout=float(settings.MODEL_REQUEST_TIMEOUT)):
            try:
                initial_snap = self.monitor.get_memory_snapshot()
                metrics["peak_vram_mb"] = max(metrics["peak_vram_mb"], initial_snap.used_mb)

                if self._state not in (ExecutionState.IDLE,):
                    logger.warning(f"GPU state was {self._state.value} at DeepSeek start. Attempting recovery...")
                    await self.attempt_recovery()

                reusing_prewarm = False
                if self._prewarmed_model == "deepseek":
                    if await self.deepseek.is_model_loaded():
                        reusing_prewarm = True
                        logger.info("Reusing prewarmed DeepSeek model instance.")
                        self._transition_to(ExecutionState.DEEPSEEK_ACTIVE, active_model="deepseek")
                    else:
                        logger.warning("DeepSeek was marked prewarmed but is no longer loaded. Reloading...")
                        self._prewarmed_model = None

                if not reusing_prewarm:
                    self._transition_to(ExecutionState.DEEPSEEK_LOADING, active_model="deepseek")
                    t0 = time.time()
                    await self.deepseek.load_model(context_length=context_length)
                    metrics["deepseek_load_ms"] = (time.time() - t0) * 1000.0
                    self._transition_to(ExecutionState.DEEPSEEK_ACTIVE, active_model="deepseek")

                snap = self.monitor.get_memory_snapshot()
                metrics["peak_vram_mb"] = max(metrics["peak_vram_mb"], snap.used_mb)

                t0 = time.time()
                reasoning_result = await reasoning_task()
                metrics["deepseek_inference_ms"] = (time.time() - t0) * 1000.0

                self._transition_to(ExecutionState.DEEPSEEK_UNLOADING, active_model="deepseek")
                t0 = time.time()
                await self.deepseek.unload_model()
                metrics["deepseek_unload_ms"] = (time.time() - t0) * 1000.0

                is_ds_loaded = await self.deepseek.is_model_loaded()
                if is_ds_loaded:
                    raise ModelUnloadError("DeepSeek model is still resident in memory after unload verification!")

                self._prewarmed_model = None
                self._active_model = None
                self._transition_to(ExecutionState.IDLE)
                return {
                    "result": reasoning_result,
                    "metrics": metrics,
                }
            except asyncio.CancelledError:
                logger.warning("DeepSeek execution was cancelled. Initiating emergency recovery...")
                self._state = ExecutionState.ERROR
                await self.attempt_recovery()
                raise
            except Exception as e:
                logger.error(f"Error during DeepSeek execution: {e}. Transitioning to ERROR.")
                self._state = ExecutionState.ERROR
                await self.attempt_recovery()
                raise e

    async def execute_llama(
        self,
        formatting_task: Callable[[], Any],
        context_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes Llama inference under GPU lock protection:
        1. Acquire GPU lock
        2. Ensure clean initial state (recover if needed)
        3. Load Llama
        4. Run formatting_task
        5. Unload Llama and verify memory cleanup
        6. Optional DeepSeek think-time prewarming
        7. Transition back to IDLE
        """
        metrics = {
            "llama_load_ms": 0.0,
            "llama_inference_ms": 0.0,
            "llama_unload_ms": 0.0,
            "peak_vram_mb": 0.0,
        }
        async with self.acquire_gpu(timeout=float(settings.MODEL_REQUEST_TIMEOUT)):
            try:
                initial_snap = self.monitor.get_memory_snapshot()
                metrics["peak_vram_mb"] = max(metrics["peak_vram_mb"], initial_snap.used_mb)

                if self._state not in (ExecutionState.IDLE,):
                    logger.warning(f"GPU state was {self._state.value} at Llama start. Attempting recovery...")
                    await self.attempt_recovery()

                self._transition_to(ExecutionState.LLAMA_LOADING, active_model="llama")
                t0 = time.time()
                await self.llama.load_model(context_length=context_length)
                metrics["llama_load_ms"] = (time.time() - t0) * 1000.0
                self._transition_to(ExecutionState.LLAMA_ACTIVE, active_model="llama")

                snap = self.monitor.get_memory_snapshot()
                metrics["peak_vram_mb"] = max(metrics["peak_vram_mb"], snap.used_mb)

                t0 = time.time()
                formatting_result = await formatting_task()
                metrics["llama_inference_ms"] = (time.time() - t0) * 1000.0

                self._transition_to(ExecutionState.LLAMA_UNLOADING, active_model="llama")
                t0 = time.time()
                await self.llama.unload_model()
                metrics["llama_unload_ms"] = (time.time() - t0) * 1000.0

                is_llama_loaded = await self.llama.is_model_loaded()
                if is_llama_loaded:
                    raise ModelUnloadError("Llama model is still resident in memory after unload verification!")

                self._active_model = None

                if self.prewarm_mode == "enabled":
                    logger.info("Executing Think-Time Prewarming for DeepSeek...")
                    self._transition_to(ExecutionState.DEEPSEEK_PREWARMING, active_model="deepseek")
                    try:
                        await self.deepseek.load_model(context_length=settings.LMSTUDIO_CONTEXT_LENGTH)
                        self._prewarmed_model = "deepseek"
                        logger.info("DeepSeek successfully prewarmed for subsequent student interaction.")
                    except Exception as e:
                        logger.warning(f"Think-time prewarming encountered error: {e}. Safe fallback to IDLE.")
                        self._prewarmed_model = None

                self._state = ExecutionState.IDLE
                self._active_model = None
                return {
                    "result": formatting_result,
                    "metrics": metrics,
                }
            except asyncio.CancelledError:
                logger.warning("Llama execution was cancelled. Initiating emergency recovery...")
                self._state = ExecutionState.ERROR
                await self.attempt_recovery()
                raise
            except Exception as e:
                logger.error(f"Error during Llama execution: {e}. Transitioning to ERROR.")
                self._state = ExecutionState.ERROR
                await self.attempt_recovery()
                raise e

    async def execute_turn(
        self,
        reasoning_task: Callable[[], Any],
        formatting_task: Callable[[Any], Any],
        deepseek_context_length: Optional[int] = None,
        llama_context_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes a complete sequential learning turn:
        1. Acquire GPU execution lock
        2. Verify GPU availability
        3. Load DeepSeek if needed
        4. Run DeepSeek reasoning inference
        5. Unload DeepSeek and verify absent from memory
        6. Load Llama
        7. Run Llama formatting inference
        8. Unload Llama and verify absent from memory
        9. Optional DeepSeek think-time prewarming
        10. Release execution lock
        """
        metrics = {
            "deepseek_load_ms": 0.0,
            "deepseek_inference_ms": 0.0,
            "deepseek_unload_ms": 0.0,
            "llama_load_ms": 0.0,
            "llama_inference_ms": 0.0,
            "llama_unload_ms": 0.0,
            "total_turn_ms": 0.0,
            "peak_vram_mb": 0.0,
        }
        turn_start = time.time()

        async with self.acquire_gpu(timeout=float(settings.MODEL_REQUEST_TIMEOUT)):
            try:
                # -----------------------------------------------------------------
                # Step 1: Verify GPU Availability & Clean Initial State
                # -----------------------------------------------------------------
                initial_snap = self.monitor.get_memory_snapshot()
                metrics["peak_vram_mb"] = max(metrics["peak_vram_mb"], initial_snap.used_mb)

                # Check if unexpected models are already resident
                if self._state not in (ExecutionState.IDLE,):
                    logger.warning(f"GPU state was {self._state.value} at turn start. Attempting recovery...")
                    await self.attempt_recovery()

                # -----------------------------------------------------------------
                # Step 2: Load DeepSeek (or reuse prewarmed instance)
                # -----------------------------------------------------------------
                reusing_prewarm = False
                if self._prewarmed_model == "deepseek":
                    # Verify model is indeed still resident in LM Studio
                    if await self.deepseek.is_model_loaded():
                        reusing_prewarm = True
                        logger.info("Reusing prewarmed DeepSeek model instance.")
                        self._transition_to(ExecutionState.DEEPSEEK_ACTIVE, active_model="deepseek")
                    else:
                        logger.warning("DeepSeek was marked prewarmed but is no longer loaded. Reloading...")
                        self._prewarmed_model = None

                if not reusing_prewarm:
                    self._transition_to(ExecutionState.DEEPSEEK_LOADING, active_model="deepseek")
                    t0 = time.time()
                    await self.deepseek.load_model(context_length=deepseek_context_length)
                    metrics["deepseek_load_ms"] = (time.time() - t0) * 1000.0
                    self._transition_to(ExecutionState.DEEPSEEK_ACTIVE, active_model="deepseek")

                # Snapshot VRAM
                snap = self.monitor.get_memory_snapshot()
                metrics["peak_vram_mb"] = max(metrics["peak_vram_mb"], snap.used_mb)

                # -----------------------------------------------------------------
                # Step 3: Run DeepSeek Reasoning Inference
                # -----------------------------------------------------------------
                t0 = time.time()
                reasoning_result = await reasoning_task()
                metrics["deepseek_inference_ms"] = (time.time() - t0) * 1000.0

                # -----------------------------------------------------------------
                # Step 4: Unload DeepSeek & Verify Absent
                # -----------------------------------------------------------------
                self._transition_to(ExecutionState.DEEPSEEK_UNLOADING, active_model="deepseek")
                t0 = time.time()
                await self.deepseek.unload_model()
                metrics["deepseek_unload_ms"] = (time.time() - t0) * 1000.0

                # Verify absent from LM Studio memory
                is_ds_loaded = await self.deepseek.is_model_loaded()
                if is_ds_loaded:
                    raise ModelUnloadError("DeepSeek model is still resident in memory after unload verification!")

                self._prewarmed_model = None
                self._active_model = None

                # -----------------------------------------------------------------
                # Step 5: Load Llama
                # -----------------------------------------------------------------
                self._transition_to(ExecutionState.LLAMA_LOADING, active_model="llama")
                t0 = time.time()
                await self.llama.load_model(context_length=llama_context_length)
                metrics["llama_load_ms"] = (time.time() - t0) * 1000.0
                self._transition_to(ExecutionState.LLAMA_ACTIVE, active_model="llama")

                snap = self.monitor.get_memory_snapshot()
                metrics["peak_vram_mb"] = max(metrics["peak_vram_mb"], snap.used_mb)

                # -----------------------------------------------------------------
                # Step 6: Run Llama Formatting Inference
                # -----------------------------------------------------------------
                t0 = time.time()
                formatting_result = await formatting_task(reasoning_result)
                metrics["llama_inference_ms"] = (time.time() - t0) * 1000.0

                # -----------------------------------------------------------------
                # Step 7: Unload Llama & Verify Absent
                # -----------------------------------------------------------------
                self._transition_to(ExecutionState.LLAMA_UNLOADING, active_model="llama")
                t0 = time.time()
                await self.llama.unload_model()
                metrics["llama_unload_ms"] = (time.time() - t0) * 1000.0

                # Verify absent from Ollama memory
                is_llama_loaded = await self.llama.is_model_loaded()
                if is_llama_loaded:
                    raise ModelUnloadError("Llama model is still resident in memory after unload verification!")

                self._active_model = None

                # -----------------------------------------------------------------
                # Step 8: Optional DeepSeek Think-Time Prewarming
                # -----------------------------------------------------------------
                if self.prewarm_mode == "enabled":
                    logger.info("Executing Think-Time Prewarming for DeepSeek...")
                    self._transition_to(ExecutionState.DEEPSEEK_PREWARMING, active_model="deepseek")
                    try:
                        await self.deepseek.load_model(context_length=deepseek_context_length)
                        self._prewarmed_model = "deepseek"
                        logger.info("DeepSeek successfully prewarmed for subsequent student interaction.")
                    except Exception as e:
                        logger.warning(f"Think-time prewarming encountered error: {e}. Safe fallback to IDLE.")
                        self._prewarmed_model = None

                # Transition cleanly back to IDLE
                self._state = ExecutionState.IDLE
                self._active_model = None
                metrics["total_turn_ms"] = (time.time() - turn_start) * 1000.0

                return {
                    "reasoning_result": reasoning_result,
                    "formatting_result": formatting_result,
                    "metrics": metrics,
                }

            except asyncio.CancelledError:
                logger.warning("GPU execution turn was cancelled. Initiating emergency recovery...")
                self._state = ExecutionState.ERROR
                await self.attempt_recovery()
                raise
            except Exception as e:
                logger.error(f"Error during GPU execution turn: {e}. Transitioning to ERROR.")
                self._state = ExecutionState.ERROR
                await self.attempt_recovery()
                raise e
