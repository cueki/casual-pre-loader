from argparse import ArgumentParser, Namespace, Action
from typing import Iterable, Optional

from core.constants import DESCRIPTION, PROGRAM_AUTHOR, PROGRAM_NAME
from core.version import VERSION


class BooleanOptionalAction(Action):
    """
    Based on argparse.BooleanOptionalAction
    """

    def __init__(
        self,
        option_strings,
        dest,
        default,
        required=False,
        help=None,
        deprecated=False
    ):
        def make_inverse_opt(opt: str) -> str:
            if opt.startswith('--'):
                return f'--no-{opt[2:]}'
            else:
                return opt.swapcase()

        length = len(option_strings)
        if not (
            length == 1
            or (
                length == 2
                and option_strings[0].startswith('-')
                and not option_strings[0].startswith('--')
                and option_strings[1].startswith('--')
            )
        ):
            raise ValueError('BooleanOptionalAction must be given one form of each format at most')

        _option_strings = option_strings.copy()
        for option_string in option_strings:
            _option_strings.append(make_inverse_opt(option_string))

        help = f'{help} ({default})'

        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            nargs=0,
            default=default,
            required=required,
            help=help,
            deprecated=deprecated,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string in self.option_strings:
            setattr(namespace, self.dest, not (self.option_strings.index(option_string) % 2))

    def format_usage(self):
        if len(self.option_strings) == 2:
            return ' | '.join(self.option_strings)
        else:
            return ' | '.join(self.option_strings[::2])


def parse_args(args: Optional[Iterable[str]] = None, namespace: Optional[Namespace] = None) -> Namespace:
    parser = ArgumentParser(
        prog=PROGRAM_NAME,
        epilog=f'Copyright (c) 2026 {PROGRAM_AUTHOR}',
        description=DESCRIPTION,
    )

    parser.add_argument(
        '-m', '--migrate',
        default=True,
        action=BooleanOptionalAction,
        help='Migrate userdata from old locations to new ones.'
    )

    parser.add_argument(
        '-p', '--portable',
        dest='portable',
        action=BooleanOptionalAction,
        default=True,
        help='Run portably, i.e. keep all userdata in `userdata/` instead of the appropriate user-specific locations depending on the OS. Has no effect if installed via package manager.'
    )

    parser.add_argument(
        '-u', '--update',
        default=True,
        action=BooleanOptionalAction,
        help='Automatically check for updates on startup. Has no effect if installed via package manager.'
    )

    parser.add_argument(
        '-v', '--verbose',
        default=False,
        action='store_true',
        help='Print more verbose information to output'
    )

    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {VERSION}'
    )

    return parser.parse_args(args=args, namespace=namespace)
