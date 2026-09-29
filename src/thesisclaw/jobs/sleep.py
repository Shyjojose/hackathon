from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def idle_sleep_loop(interval_seconds: int = 3600, max_iterations: int | None = None) -> None:
    """Asynchronous background loop that keeps the agent active between scheduled scans."""
    logger.info("ThesisClaw idle loop started (interval: %ds)", interval_seconds)
    iterations = 0
    try:
        while True:
            iterations += 1
            logger.info("Heartbeat: Agent active. Sleeping for %ds...", interval_seconds)
            await asyncio.sleep(interval_seconds)
            if max_iterations is not None and iterations >= max_iterations:
                break
    except asyncio.CancelledError:
        logger.info("Idle sleep loop cancelled gracefully.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(idle_sleep_loop())
    except KeyboardInterrupt:
        print("\nAgent stopped by user.")


if __name__ == "__main__":
    main()
