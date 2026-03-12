from argparse import ArgumentParser, Namespace
from typing import Iterable, Optional

from core.constants import DESCRIPTION, PROGRAM_AUTHOR, PROGRAM_NAME
from core.version import VERSION


def parse_args(args: Optional[Iterable[str]] = None, namespace: Optional[Namespace] = None) -> Namespace:
    parser = ArgumentParser(
        prog=PROGRAM_NAME,
        epilog=f'Copyright (c) 2026 {PROGRAM_AUTHOR}',
        description=DESCRIPTION,
    )

    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {VERSION}'
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

    parser.add_argument(
        '-U', '--no-update',
        dest='update',
        action='store_false',
        help='Skip the automatic update check on startup'
    )

    parser.add_argument(
        '--tf-dir',
        type=str,
        default=None,
        help='Override the TF2 directory path'
    )

    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset settings to defaults and re-run first-time setup'
    )

    return parser.parse_args(args=args, namespace=namespace)
