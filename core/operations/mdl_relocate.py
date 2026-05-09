"""
MDL material-directory relocation pass for the install pipeline.

For each MDL in the staged mod tree, rewrites its materialDirectories[] so the
mod's material trees live under a the console prefix, while preserving the
un-relocated original paths as fallbacks.

Pipeline (run in order):

  1. relocate_mdl_dirs       - rewrite each MDL's material_dirs (prefixed at
                                original index, original appended for vanilla
                                fallback) and physically move
                                materials/<old>/ -> materials/<prefix>/<old>/
  2. relocate_material_names - re-prefix path-rooted material name entries
                                (some MDLs bake the path into the name when
                                $cdmaterials is blank)
  3. update_vmt_refs         - rewrite $basetexture / $bumpmap / etc. references
                                inside every VMT to point at the new location
                                when the relocated VTF/VMT exists there
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from valve_parsers import MDLFile

from core.util.file import move

log = logging.getLogger()

DEFAULT_PREFIX = "console"

# Material dirs under these roots are already fixed, so they
# don't need relocation. Rewriting them would also change the author's
# intended search-order override semantics.
SAFE_PATH_ROOTS = ("console", "vgui/replay/thumbnails")

# Characters that can appear after a relocated prefix in a Source-engine
# material path reference. Used to greedily extend each match to the full
# referenced path so we can verify the file exists at the new location.
_PATH_TAIL_CHARS = r"[A-Za-z0-9_./\-]"


@dataclass
class Relocation:
    old_dir: str  # /-form with trailing slash, e.g. "models/player/items/scout/"
    new_dir: str  # /-form with trailing slash, e.g. "console/models/player/items/scout/"


def _norm(path: str) -> str:
    return path.replace("\\", "/").lower()


def _is_under_safe_root(dir_str: str) -> bool:
    normalized = dir_str.lstrip("/").lower()
    return any(normalized.startswith(root + "/") for root in SAFE_PATH_ROOTS)


def add_prefix(dir_str: str, prefix: str) -> str:
    """Prepend prefix to a material dir.

    Empty and lone-root entries (`/`) are left untouched. Prefixing
    them would (a) be meaningless as a search path, (b) scoop up the entire
    materials/ tree on disk if we tried to move it, and (c) generate a
    text-replace rewrite of `/` -> `console/` that catastrophically corrupts
    every VMT it touches.
    """
    if (
        not dir_str
        or dir_str == "/"
        or _is_under_safe_root(dir_str)
        or dir_str.lower().startswith(f"{prefix}/".lower())
    ):
        return dir_str
    stripped = dir_str.lstrip("/")
    return f"{prefix}/{stripped}"


def resolve_ci(root: Path, rel_path: str) -> Path | None:
    """Resolve `rel_path` under `root` case-insensitively, the way the Source
    engine does on Windows. Linux is case-sensitive, but a mod authored on
    Windows can ship files whose case differs from the MDL's references; plain
    `Path.exists()` would say 'missing' and trigger spurious work.
    """
    rel = _norm(rel_path).strip("/")
    if not rel:
        return root if root.exists() else None
    current = root
    for part in rel.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if current == root:
                return None
            current = current.parent
            if not current.exists():
                return None
            continue
        target = part.lower()
        try:
            match = next((e for e in current.iterdir() if e.name.lower() == target), None)
        except (OSError, NotADirectoryError):
            return None
        if match is None:
            return None
        current = match
    return current


def _relocate_one_mdl(mdl_path: Path, working_root: Path, prefix: str) -> list[Relocation]:
    """Rewrite one MDL's material_dirs to use the prefix and move on-disk
    material trees to match.

    For each relocated entry we put the prefixed path *at the original index*
    (so the engine searches mod content first within that slot) and append the
    un-relocated original to the end of the list. Keeping the original gives
    the engine a path to reach vanilla VMTs that the mod doesn't ship + the
    mod sometimes populates a directory only partially and relies on engine
    fallback for shared textures (eyeballs, masks, invuln effects, etc.).
    Without the fallback path in the search list, those vanilla materials
    become unreachable.
    """
    mdl = MDLFile(mdl_path)
    materials_root = working_root / "materials"

    new_dirs: list[str] = []
    fallback_dirs: list[str] = []  # un-relocated paths appended at end
    relocations: list[Relocation] = []

    rel_mdl = mdl_path.relative_to(working_root)
    log.debug(f"[{rel_mdl}]")

    for raw in mdl.material_dirs:
        # Some MDLs store material_dirs with a leading slash (e.g.
        # "/models/player/items/sniper/"). The engine treats these the same
        # as the slash-less form, but if we kept the leading slash it would
        # leak into Relocation.old_dir and cause the VMT-rewrite regex to
        # look for "/models/foo/" in source text that only ever writes
        # "models/foo/", silently missing every reference.
        old = _norm(raw).lstrip("/")
        proposed = add_prefix(old, prefix)
        if old == proposed:
            new_dirs.append(old)
            continue

        old_rel = old.rstrip("/")
        new_rel = proposed.rstrip("/")
        src = resolve_ci(materials_root, old_rel)
        dst = resolve_ci(materials_root, new_rel)
        canonical_dst = materials_root / new_rel

        if src is None and dst is None:
            new_dirs.append(old)
            log.debug(f"skip: materials/{old_rel}/ not present in mod")
            continue

        new_dirs.append(proposed)
        if old not in fallback_dirs:
            fallback_dirs.append(old)
        relocations.append(Relocation(
            old_dir=old.rstrip("/") + "/",
            new_dir=proposed.rstrip("/") + "/",
        ))
        log.debug(f"rewrote material_dir: {old!r} -> {proposed!r}  (kept {old!r} as fallback)")

        if dst is not None and (src is None or src != dst):
            log.debug(f"on-disk: materials/{new_rel}/ already exists (moved by another MDL)")
            continue
        move(src, canonical_dst)
        for parent in src.parents:
            if parent == materials_root:
                break
            try:
                parent.rmdir()
            except OSError:
                break
        log.debug(f"moved on-disk: materials/{old_rel}/ -> materials/{new_rel}/")

    mdl.rewrite_material_dirs(new_dirs + fallback_dirs)
    return relocations


def _build_rewrite_regex(
    relocations: list[Relocation],
) -> tuple[re.Pattern[str] | None, dict[str, str] | None]:
    """Build a single-pass regex + mapping from a list of relocations.

    Prefixes are sorted longest-first so a more specific rule wins. The
    path-char lookbehind anchors the match to a path-token boundary;
    without it, an already-prefixed path would match an inner rule and
    get a doubled prefix. The extra `(?<=materials/)` alternative carves
    out the one place where matching after a `/` is desirable: Patch VMT
    `include "materials/..."` directives. Without that carve-out, those
    includes never get rewritten when their target file gets relocated.
    """
    pairs = sorted(
        {(r.old_dir, r.new_dir) for r in relocations},
        key=lambda p: len(p[0]),
        reverse=True,
    )
    if not pairs:
        return None, None
    prefix_alt = "|".join(re.escape(old) for old, _ in pairs)
    pattern = re.compile(
        f"(?:(?<=materials/)|(?<!{_PATH_TAIL_CHARS}))"
        f"(?P<prefix>{prefix_alt})(?P<tail>{_PATH_TAIL_CHARS}*)",
        re.IGNORECASE,
    )
    mapping = dict(pairs)
    return pattern, mapping


def _apply_path_rewrites(
    text: str,
    pattern: re.Pattern[str] | None,
    mapping: dict[str, str] | None,
    materials_root: Path,
) -> str:
    """Rewrite path refs whose target file exists at the new location; leave
    refs that don't (they're relying on engine fallback to vanilla).
    """
    if pattern is None or mapping is None:
        return text

    def replace(m: re.Match[str]) -> str:
        prefix = m.group("prefix")
        tail = m.group("tail")
        new_prefix = mapping[prefix.lower()]
        if not tail:
            return new_prefix
        full_new = new_prefix + tail
        last_segment = tail.rsplit("/", 1)[-1]
        if "." in last_segment:
            candidates = (full_new,)
        else:
            candidates = (full_new + ".vtf",)
        if any(resolve_ci(materials_root, c) is not None for c in candidates):
            return new_prefix + tail
        return m.group(0)

    return pattern.sub(replace, text)


def _relocate_material_names(working_root: Path, mdl_paths: list[Path], relocations: list[Relocation]) -> None:
    """Rewrite per-material name strings whose path-rooted prefix matches a
    relocation. Some MDLs reference materials by full path (e.g. material name
    'models/weapons/c_items/c_buffbanner' paired with an empty material_dir);
    the engine resolves these via 'materials/<name>.vmt'. When that on-disk
    location has been moved, the name itself must be re-prefixed.

    Each rewrite is gated on the candidate VMT existing at the new location.
    Without that check, an MDL that references both a mod-shipped material
    *and* a vanilla material under the same prefix would have both names
    re-prefixed; the vanilla one would then point at materials/console/...
    where nothing was shipped, and the engine has no path back to the
    original vanilla VMT.
    """
    if not relocations:
        return
    pairs = sorted(
        {(r.old_dir, r.new_dir) for r in relocations},
        key=lambda p: len(p[0]),
        reverse=True,
    )
    materials_root = working_root / "materials"

    def rewrite_name(name: str) -> str:
        normalized = _norm(name).lstrip("/")
        if "/" not in normalized:
            return name
        for old, new in pairs:
            if normalized.startswith(old):
                candidate = new + normalized[len(old):] + ".vmt"
                if resolve_ci(materials_root, candidate) is None:
                    return name
                return new + normalized[len(old):]
        return name

    for mdl_path in mdl_paths:
        mdl = MDLFile(mdl_path)
        new_names = [rewrite_name(m) for m in mdl.materials]
        if new_names == mdl.materials:
            continue
        mdl.rewrite_materials(new_names)
        for old, new in zip(mdl.materials, new_names):
            if old != new:
                log.debug(f"[{mdl_path.name}] rewrote material name: {old!r} -> {new!r}")


def _update_vmt_refs(working_root: Path, relocations: list[Relocation]) -> None:
    """Walk every VMT and rewrite references to any relocated path. Each
    candidate rewrite is gated on the target file existing at the new
    location, so refs that fall through to vanilla stay intact.
    """
    pattern, mapping = _build_rewrite_regex(relocations)
    if pattern is None:
        return
    materials_root = working_root / "materials"
    if not materials_root.exists():
        return
    for vmt in materials_root.rglob("*.vmt"):
        original = vmt.read_text(encoding="utf-8", errors="replace")
        text = original.replace("\\", "/")
        new_text = _apply_path_rewrites(text, pattern, mapping, materials_root)
        if new_text != original:
            vmt.write_text(new_text, encoding="utf-8")
            log.debug(f"rewrote refs in materials/{vmt.relative_to(materials_root)}")


def relocate_mdl_paths(
    working_root: Path,
    prefix: str = DEFAULT_PREFIX,
) -> int:
    """Run the full MDL-relocation pipeline against a staged mod tree.

    Returns the number of MDLs found.
    """
    mdl_paths = sorted(working_root.rglob("*.mdl"))
    if not mdl_paths:
        return 0

    log.info(f"Relocating material paths for {len(mdl_paths)} MDL(s) under prefix '{prefix}'")

    all_relocations: list[Relocation] = []
    for mdl_path in mdl_paths:
        try:
            all_relocations.extend(_relocate_one_mdl(mdl_path, working_root, prefix))
        except Exception:
            log.exception(f"MDL relocation failed for {mdl_path}; leaving as-is")

    try:
        _relocate_material_names(working_root, mdl_paths, all_relocations)
    except Exception:
        log.exception("MDL material-name rewrite failed")

    try:
        _update_vmt_refs(working_root, all_relocations)
    except Exception:
        log.exception("VMT reference rewrite failed")

    return len(mdl_paths)
