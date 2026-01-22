from argparse import ArgumentParser, Namespace
from typing import Iterable, Optional

from core.constants import DESCRIPTION, PROGRAM_AUTHOR, PROGRAM_NAME


def parse_args(args: Optional[Iterable[str]] = None, namespace: Optional[Namespace] = None) -> Namespace:
    parser = ArgumentParser(
        prog=PROGRAM_NAME,
        epilog=f'Copyright (c) 2026 {PROGRAM_AUTHOR}',
        description=DESCRIPTION,
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '-M', '--no-migrate',
        dest='migrate',
        action='store_false',
        help='Do not try to migrate userdata from old locations to new ones after updating'
    )

    return parser.parse_args(args=args, namespace=namespace)
