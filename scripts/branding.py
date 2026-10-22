"""The loader's human-facing name: one file (branding.json), display only.

Nothing functional is derived from it. Identity and protocol are separate and fixed (docs/IDENTITY.md): the
`CowboyBingusModLoader` global and API marker that every mod looks up, the manager GUID, the log file name, the
log's first-line format and the console prefix. Renaming the loader means editing branding.json and nothing else.

    name           shown in the mod manager, in the build description and in docs
    short_name     used in prose
    artifact_stem  file-name stem: <stem>-vN.zip, <stem>-manifest.json, <stem>-README.txt
    icon           (optional) the box icon, a PNG under assets/; packaged as thumbnail.png
    pack           display name / file stem of the gameplay pack this loader is documented alongside
    previous       earlier brands, so .github/scripts/rebrand.py can rewrite docs that still use them
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Names go inside Python/JSON strings and docs: no quotes, backslashes or control characters.
NAME = re.compile(r"[^\x00-\x1f\x7f'\"\\]{1,64}")
STEM = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,47}')
ICON = re.compile(r'assets/(?:[A-Za-z0-9_-][A-Za-z0-9._-]*/)*[A-Za-z0-9_-][A-Za-z0-9._-]*\.png')


def _pair(entry, where):
    if not isinstance(entry, dict) or not NAME.fullmatch(entry.get('name', '')) or \
            not STEM.fullmatch(entry.get('artifact_stem', '')):
        raise ValueError(f'branding.json: invalid {where}: {entry!r}')


def validate(branding):
    if not isinstance(branding, dict):
        raise ValueError('branding.json must be an object')
    for key, pattern in (('name', NAME), ('short_name', NAME), ('artifact_stem', STEM)):
        value = branding.get(key)
        if not isinstance(value, str) or not pattern.fullmatch(value) or value != value.strip():
            raise ValueError(f'branding.json: invalid {key}: {value!r}')
    if len(branding['short_name']) > 16:
        raise ValueError('branding.json: short_name is longer than 16 characters')
    icon = branding.get('icon')
    if icon is not None and (not isinstance(icon, str) or not ICON.fullmatch(icon) or '..' in icon):
        raise ValueError(f'branding.json: invalid icon: {icon!r}')
    for old in branding.get('previous', []):
        _pair(old, 'previous entry')
    pack = branding.get('pack')
    if pack is not None:
        _pair(pack, 'pack')
        for old in pack.get('previous', []):
            _pair(old, 'pack previous entry')
    return branding


def load(root=ROOT):
    return validate(json.loads((Path(root) / 'branding.json').read_text(encoding='utf-8')))
