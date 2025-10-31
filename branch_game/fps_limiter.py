import time
from typing import Callable


def create_fps_limiter(
    fps: float,
    poll_interval: float = 0.003,
    spin_reserve: float = 0.001,
) -> Callable[[], float]:
    """
    Create a drift-correcting frame limiter.

    Returns:
        wait_for_next_frame() -> float
            Call this *after* your tick()/frame work. It enforces the target FPS
            (hybrid sleep + short busy-wait) and returns the actual frame time (dt).
    """
    target = 1.0 / float(fps)
    poll_interval = float(poll_interval)
    spin_reserve = float(spin_reserve)
    # schedule first frame to end target seconds from now
    next_frame = time.perf_counter() + target

    def wait_for_next_frame() -> float:
        nonlocal next_frame
        now = time.perf_counter()

        if now < next_frame:
            sleep_until = next_frame - spin_reserve if spin_reserve > 0 else next_frame
            # sleep-poll loop (low CPU, reasonable accuracy)
            while time.perf_counter() < sleep_until:
                time.sleep(min(poll_interval, sleep_until - time.perf_counter()))
            # short busy-wait to tighten timing
            if spin_reserve > 0:
                while time.perf_counter() < next_frame:
                    pass
            end = time.perf_counter()
            dt = end - (next_frame - target)  # actual frame duration
            next_frame += target
            return dt

        # we're behind schedule: compute dt since last frame and advance schedule
        dt = now - (next_frame - target)
        while next_frame <= now:
            next_frame += target
        return dt

    return wait_for_next_frame
