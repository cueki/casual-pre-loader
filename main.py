#!/usr/bin/env python3

import logging

from rich.logging import RichHandler
from rich.traceback import install


def main() -> None:
    logger = logging.getLogger() # explicitly get the root logger

    handler = RichHandler(rich_tracebacks=True)
    handler.setFormatter(logging.Formatter(datefmt='[%Y-%m-%d %H:%M:%S]'))
    logger.addHandler(handler)

    logger.setLevel(logging.INFO)

    from core.config import config, subcommand

    # install the rich traceback handler
    install(show_locals=config.verbose, max_frames=(not config.verbose and 100 or 0))

    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.addHandler(logging.FileHandler(config.log_file, mode='a', encoding='utf-8'))
    logger.setLevel(config.verbose and logging.DEBUG or logging.INFO)

    raise SystemExit(subcommand(config))

if __name__ == '__main__':
    main()
