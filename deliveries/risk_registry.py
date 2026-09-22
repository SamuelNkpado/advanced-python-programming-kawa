"""
Simulates the external risk registry described in the Kawa Network brief:
slow (2-40s latency) and unreliable (unavailable for stretches of time).
This stands in for a real third-party compliance API we don't have access to.
"""
import random
import time


class RegistryUnavailableError(Exception):
    """Raised when the simulated registry is 'down'."""
    pass


def check_plot_risk(plot_id: int) -> str:
    """
    Simulate a slow, occasionally-failing risk check for a plot.
    Returns 'cleared' or 'flagged' on success.
    Raises RegistryUnavailableError to simulate an outage.
    """
    # Simulate 2-40 second latency, compressed for local testing.
    # (In a real run you'd use the full range; we use a shorter range
    # here so testing doesn't take 40 seconds per check.)
    time.sleep(random.uniform(2, 6))

    # Simulate the registry being down ~20% of the time.
    if random.random() < 0.2:
        raise RegistryUnavailableError(f"Registry unavailable for plot {plot_id}")

    # Simulate a mostly-clean result set, with occasional flags.
    return 'flagged' if random.random() < 0.15 else 'cleared'