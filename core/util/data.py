import json
import logging
from collections.abc import Mapping
from types import MappingProxyType

from core.config import config

# TODO: change to frozendict once we hit python 3.15 minimum version
type ModUrls = Mapping[str, str]


def load_mod_urls() -> ModUrls:
    try:
        with config.mod_urls_file.open('r') as fd:
            return MappingProxyType(json.load(fd))
    except Exception:
        logging.exception('Error loading mod URLs')
        raise


mod_urls: ModUrls


def __getattr__(attr):
    global mod_urls

    match attr:
        case 'mod_urls':
            mod_urls = load_mod_urls()
            return mod_urls

    raise AttributeError(f"module '{__name__}' has no attribute '{attr}'")
