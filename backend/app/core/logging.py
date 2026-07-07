import sys

from loguru import logger

_FORMAT = (
    "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
)


def configure_logging(debug: bool) -> None:
    """Single sink, one readable format, for every log line in the app.

    diagnose=False is deliberate: loguru's diagnose mode prints local variable
    values in tracebacks, which would leak API keys held on provider objects
    (self._api_key) into the log the moment an LLM call raised.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if debug else "INFO",
        format=_FORMAT,
        colorize=True,
        backtrace=True,
        diagnose=False,
    )
