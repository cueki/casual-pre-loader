from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import cast

from cappa import Arg, ArgAction, Destructured, Group, Subcommand, command, parse
from typing_extensions import Annotated

from core.constants import DESCRIPTION, PROGRAM_AUTHOR, PROGRAM_NAME, Sourcemods
from core.folder_setup import FolderConfig
from core.util.sourcemod import (
    auto_detect_sourcemod,
    get_sourcemod,
    validate_game_directory,
)
from core.version import VERSION


# The meat and potatoes
@dataclass
class Args:
    migrate: Annotated[bool, Arg(short='-M', long='--no-migrate')] = True
    """Migrate userdata from old locations to new ones."""

    # we may only be portable if the application was not packaged with a dummy `.noportable` file
    portable: Annotated[bool, Arg(short='-P', long='--no-portable', action=ArgAction.store_false)] = FolderConfig.portable
    """Run portably, i.e. keep all userdata in `userdata/` instead of the appropriate user-specific locations depending on the OS. Has no effect and is always false if installed via package manager."""

    # NOTE: probably best to remove and replace with `--profile`
    sourcemod: Annotated[Sourcemods, Arg(parse=get_sourcemod)] = Sourcemods.DEFAULT
    """Specify which sourcemod to target. Takes either a name or a steam id."""

    # NOTE: probably best to remove and replace with `--profile`
    tf_dir: Path = None # ty: ignore[invalid-assignment]
    """Override the tf directory path."""

    update: Annotated[bool, Arg(short='-U', long='--no-update', action=ArgAction.store_false)] = FolderConfig.portable
    """Automatically check for updates on startup. Has no effect and is always false if installed via package manager."""

    verbose: Annotated[bool, Arg(short=True, propagate=True)] = False
    """Increase the verbosity of log messages."""

    def __post_init__(self) -> None:
        if self.tf_dir is None:
            self.tf_dir = auto_detect_sourcemod(self.sourcemod)
        else:
            if not validate_game_directory(self.tf_dir):
                logging.critical(f'--tf-dir is not a valid Source mod directory: {self.tf_dir}')
                raise SystemExit(1)


@command
@dataclass
class Gui:
    """Opens the GUI (default)"""
    def __call__(self, config: Config) -> int:
        from main import gui, log_start

        log_start()

        if config.migrate:
            import core.migrations
            core.migrations.migrate()

        return gui()


@command(name='print_sourcemods')
@dataclass
class PrintSourcemods:
    """Print all known sourcemods, their aliases and steam IDs."""
    def __call__(self, config: Config) -> int:
        from rich import print as pprint

        for sourcemod in Sourcemods:
            pprint(sourcemod)

        return 0


@command
@dataclass
class Reset:
    """Reset settings to defaults."""
    def __call__(self, config: Config) -> int:
        if not (config.app_settings_file.is_file() or config.addon_metadata_file.is_file()):
            logging.warning('Nothing to reset')
            return 0

        from rich.prompt import Confirm

        if Confirm.ask(
            'This will delete your saved profiles and settings.\n'
            'Your installed mods will not be affected.\n'
            'Are you sure?'
        ):
            from core.util.file import delete

            delete(config.app_settings_file, not_exist_ok=True)
            delete(config.addon_metadata_file, not_exist_ok=True)
            logging.warning('Settings have been reset')
            return 0
        else:
            logging.critical('Reset cancelled')
            return 1


# create a class that inherits all config dataclasess, initialize it using a union of an instance of each
# based on https://github.com/omni-us/jsonargparse/pull/796
@dataclass
class Config(Args, FolderConfig):
    def __post_init__(self) -> None:
        pass


_Subcommand = Gui | PrintSourcemods | Reset


config: Config
subcommand: _Subcommand


def _get_config() -> None:
    """
    Parses CLI args and globally sets the relevant `Config` instance and subcommand, only runs once per execution without being manually called.
    """

    @command(
        name=PROGRAM_NAME,
        default_long=True,
        epilog='Licensed under the terms of the GNU GPLv3 or any later version  \n'
        f'Copyright (c) 2026 {PROGRAM_AUTHOR}, {PROGRAM_NAME} contributors  \n'
        'For a full list of contributors, run `git shortlog -snei --group=author --group=trailer:co-authored-by`'
    )
    @dataclass
    class Cli:
        __doc__  = f'''{DESCRIPTION}
         Opens the GUI by default.
        '''

        args: Destructured[Args]

        subcommand: Annotated[_Subcommand | None, Subcommand()] = field(default_factory=Gui)
        """Subcommand to run instead of opening the gui"""

    args = parse(
        Cli,
        version=Arg(
            f'{PROGRAM_NAME} {VERSION}',
            short='-V',
            long=True,
            help="Print the version string and exit.",
            group=Group(1, 'Help', section=2),
        ),
    )

    global config, subcommand

    subcommand = cast(_Subcommand, args.subcommand)
    config = Config(**{ # shallowly copy all attrs
        field.name: getattr(args.args, field.name)
        for field in fields(args.args)
    })


def __getattr__(attr):
    match attr:
        case 'config':
            _get_config()
            return config
        case 'subcommand':
            _get_config()
            return subcommand

    raise AttributeError(f"module '{__name__}' has no attribute '{attr}'")
