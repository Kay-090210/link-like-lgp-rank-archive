import logging


def setup_logging(level=logging.INFO):
    """Configure basic logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
