import time
from typing import Callable


def create_fps_limiter(
    fps: float,
    poll_interval: float = 0.001,
    spin_reserve: float = 0.002,
) -> Callable[[], float]:
    """
    High-precision, drift-correcting frame limiter.
    Keeps perfect alignment with wall time to avoid visible jitter.
    """
    target = 1.0 / float(fps)
    next_frame = time.perf_counter() + target

    def wait_for_next_frame() -> float:
        nonlocal next_frame
        target_time = next_frame
        now = time.perf_counter()

        # --- Sleep until close to target ---
        while True:
            remaining = target_time - now - spin_reserve
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, remaining))
            now = time.perf_counter()

        # --- Spin for last couple ms for precision ---
        while time.perf_counter() < target_time:
            pass

        end = time.perf_counter()

        # --- Compute actual frame time ---
        dt = end - (next_frame - target)

        # --- Schedule next frame based on *absolute time*, not drifted increments ---
        next_frame = target_time + target

        # If we’re very late, resync instead of stacking drift
        if end > next_frame:
            next_frame = end + target

        return dt

    return wait_for_next_frame
