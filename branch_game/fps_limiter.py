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

    # Schedule the end of the first frame
    next_frame = time.perf_counter() + target

    def wait_for_next_frame() -> float:
        nonlocal next_frame
        now = time.perf_counter()

        if now < next_frame:
            # Sleep until just before the target time, then spin briefly
            sleep_until = next_frame - spin_reserve if spin_reserve > 0 else next_frame

            # Sleep-poll loop (low CPU usage, good precision)
            while True:
                remaining = sleep_until - time.perf_counter()
                if remaining <= 0:
                    break
                time.sleep(min(poll_interval, remaining))

            # Busy-wait to hit the exact target more precisely
            if spin_reserve > 0:
                while time.perf_counter() < next_frame:
                    pass

            end = time.perf_counter()
            dt = end - (next_frame - target)
            next_frame += target
            return dt

        # We're behind schedule — catch up without sleeping
        dt = now - (next_frame - target)
        while next_frame <= now:
            next_frame += target
        return dt

    return wait_for_next_frame
