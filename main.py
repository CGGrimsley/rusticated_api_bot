from __future__ import annotations

import logging
import sys

from rustinity_bot.client import bot
from rustinity_bot.config import settings
from rustinity_bot.storage import init_db

# Import commands so that all @bot.tree.command decorators run
# and register with the bot's CommandTree during setup.
import rustinity_bot.commands  # noqa: F401  (import is for side-effects only)


def configure_logging() -> None:
    """Configure basic logging for the bot."""

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Make HTTP/requests logs less noisy if needed
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def main() -> int:
    """Entry point for the Rustinity bot."""

    configure_logging()

    logger = logging.getLogger(__name__)
    logger.info("Starting Rustinity bot...")
    logger.info(
        "Using server_id=%s, wipe_id=%s", settings.server_id, settings.server_wipe_id
    )

    # Ensure database and tables exist
    init_db()

    try:
        bot.run(settings.discord_token)
    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt.")
    except Exception:
        logger.exception("Fatal error in bot run loop.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
