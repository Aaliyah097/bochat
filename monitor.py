import logging
import os
import sys


_handler = logging.StreamHandler(stream=sys.stdout)
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
)

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    handlers=[_handler],
    force=True,
)

_logger = logging.getLogger("bochat")


class Monitor:
    """Stdout-only logger. Promtail picks logs up from container stdout."""

    is_active = True

    @classmethod
    async def stop(cls):
        cls.is_active = False
        _logger.info("Монитор остановлен")

    @classmethod
    async def log(
        cls,
        msg: str,
        chat_id: int | None = None,
        user_id: int | None = None,
        unknown: bool = False,
    ) -> None:
        level = logging.ERROR if unknown else logging.INFO
        _logger.log(
            level,
            "msg=%s chat=%s user=%s",
            msg or "",
            chat_id or "",
            user_id or "",
        )

    @classmethod
    async def consume(cls):
        cls.is_active = True
        _logger.info("Монитор запущен")
