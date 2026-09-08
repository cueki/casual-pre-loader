import collections
import json
import logging

from core.config import config
from core.settings import addon_metadata
from core.util.file import delete
from core.util.text import abbrev_root

log = logging.getLogger(__name__)


class AddonService:
    def __init__(self):
        self.addons_cache = {}  # name -> addon_info mapping

    def load_addon_info(self, addon_name: str) -> dict:
        # load mod.json for a single addon, eturns default dict if not found
        addon_path = config.addons_dir / addon_name
        try:
            mod_json_path = addon_path / 'mod.json'
            if mod_json_path.exists():
                with open(mod_json_path, 'r') as addon_json:
                    try:
                        addon_info = json.load(addon_json)
                        addon_info['file_path'] = addon_name
                        return addon_info
                    except json.JSONDecodeError:
                        pass
        except FileNotFoundError:
            pass

        return {
            "addon_name": addon_name,
            "type": "Unknown",
            "description": "",
            "contents": ["Custom content"],
            "file_path": addon_name
        }

    def get_addons_grouped(self) -> dict[str, list[dict]]:
        addons_dir = config.addons_dir
        addon_groups = collections.defaultdict(list)

        self.addons_cache = {}

        addons_dir.mkdir(parents=True, exist_ok=True)
        for addon_path in addons_dir.iterdir():
            if addon_path.is_dir():
                addon_info = self.load_addon_info(addon_path.name)
                addon_type = addon_info.get("type", "unknown").lower()
                addon_groups[addon_type].append(addon_info)
                # Populate cache
                self.addons_cache[addon_info['addon_name']] = addon_info

        # sort the addon groups alphabetically
        addon_groups = {group: addon_groups[group] for group in sorted(addon_groups)}

        # sort the addons in each group alphabetically based on mod.json name
        for group in addon_groups:
            addon_groups[group].sort(key=lambda x: x['addon_name'].lower())

        return addon_groups

    def scan_addon_contents(self) -> bool:
        # scan all addon directories and cache file lists, returns True if any addons were updated
        addons_dir = config.addons_dir
        addons_dir.mkdir(parents=True, exist_ok=True)
        addons = [d for d in addons_dir.iterdir() if d.is_dir()]
        processed = 0
        new_or_updated = 0

        for addon_dir in addons:
            addon_name = addon_dir.name
            # get the last modified time of the most recently changed file
            last_modified = max((f.stat().st_mtime for f in addon_dir.glob('**/*') if f.is_file()), default=0)
            processed += 1

            # check if addon has been scanned before and hasn't changed
            if (addon_name in addon_metadata and
                    addon_metadata[addon_name].get('last_modified') == last_modified):
                continue

            # addon is new or modified, scan it
            try:
                addon_files = []
                for file_path in addon_dir.glob('**/*'):
                    if file_path.is_file() and file_path.name != 'mod.json' and file_path.name != 'sound.cache':
                        rel_path = str(file_path.relative_to(addon_dir))
                        addon_files.append(rel_path)

                new_or_updated += 1

                if addon_name not in addon_metadata:
                    addon_metadata[addon_name] = {}

                addon_metadata[addon_name].update({
                    'last_modified': last_modified,
                    'files': addon_files,
                    'file_count': len(addon_files)
                })

            except Exception:
                log.exception(f"Error scanning {addon_name}")

        addon_metadata.save()
        return new_or_updated > 0

    def delete_addons(self, mod_names: list[str]) -> None:
        '''
        Delete addon folders from the particles directory.

        Args:
            mod_names: Names of the mod folders to delete
        '''

        metadata_modified = False

        excs = []
        for mod_name in mod_names:
            mod_path = config.addons_dir / mod_name

            try:
                delete(mod_path, not_exist_ok=True)
            except OSError as e:
                errmsg = ('Failed to delete addon (%s[%d]): "%s"', e.strerror, e.errno, abbrev_root(config.addons_dir, mod_path, 'ADDONS'))
                log.error(*errmsg)
                e.add_note(errmsg[0] % errmsg[1:])
                excs.append(e)
            else:
                log.info(f'Deleted addon {mod_name}')

                if mod_name in addon_metadata:
                    del addon_metadata[mod_name]
                    metadata_modified = True

        if metadata_modified: # update addon_metadata.json if need be
            addon_metadata.save()

        if excs:
            raise ExceptionGroup('Failed to delete addons', excs)
