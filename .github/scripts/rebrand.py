#!/usr/bin/env python3
"""Apply the loader's branding (branding.json) to upstream-owned prose.

Why a script and not a one-off find-and-replace: this fork follows CowboyBingus/BingusSharedLoader. Upstream keeps
editing README.md and friends in its own brand, so hand-edited copies would conflict on every sync. The rules below
are deterministic and idempotent; the sync (sync_merge.sh) takes upstream's version of any file listed here on
conflict and re-runs this script.

The name comes from branding.json; `previous` lists earlier brands, so the same rules also work for a future rename.
Only PROSE is rewritten. The loader's protocol is never touched (docs/IDENTITY.md): the log file name, the log's
first-line format, the console prefix, the kill-switch file name and the CowboyBingusModLoader global all look like
names but are matched by machine, which is why every display-name rule below refuses to match them.
Historical statements ("Loader-v7 adds ...", "pack v31") are left as written.

    python rebrand.py            apply
    python rebrand.py --check    exit 1 if anything would change (writes nothing)
    python rebrand.py --list     print every file this script may modify
"""
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import branding  # noqa: E402

B = branding.load(ROOT)
NAME, SHORT, STEM = B['name'], B['short_name'], B['artifact_stem']
PACK = B['pack']
UPSTREAM_URL = 'https://github.com/CowboyBingus/BingusSharedLoader'


def alt(values):
    return '(?:' + '|'.join(re.escape(v) for v in sorted(values, key=len, reverse=True)) + ')'


OLD_NAMES = [p['name'] for p in B.get('previous', []) if p['name'] != NAME]
OLD_STEMS = [p['artifact_stem'] for p in B.get('previous', []) if p['artifact_stem'] != STEM]
PACK_OLD_NAMES = [p['name'] for p in PACK.get('previous', []) if p['name'] != PACK['name']]
PACK_OLD_STEMS = [p['artifact_stem'] for p in PACK.get('previous', []) if p['artifact_stem'] != PACK['artifact_stem']]
LOADER, LOADER_STEM = alt(OLD_NAMES), alt(OLD_STEMS)
PACK_NAMES, PACK_STEMS = alt(PACK_OLD_NAMES), alt(PACK_OLD_STEMS)

PROSE = [
    (rf'(Shared Mod Loader / )({LOADER})( entry)', rf'\1\2 / {NAME}\3'),
    # Display name only: never the log's first line ("Bingus Shared Loader loader-v20; API 1").
    (rf'(?<!Mod Loader / ){LOADER}(?! loader-v)', NAME),
    (r'From a BingusSharedLoader source checkout', f'From a {NAME} source checkout'),
    # The gameplay pack this loader is documented with; history ("Loader-v7 adds ...", "pack v31") stays as written.
    (rf'(?<!Loader-v7 adds ){PACK_NAMES}(?! v\d)', PACK['name']),
    (rf'{PACK_STEMS}-v(\d+)\.zip', rf'{PACK["artifact_stem"]}-v\1.zip'),
    (rf'{LOADER_STEM}-v(\d+)(-probe\d+)?\.zip', rf'{STEM}-v\1\2.zip'),
]
README_ONLY = [
    (rf'!\[{LOADER}\]\(assets/(?:mhga/)?banner\.png\)', f'![{NAME}](assets/mhga/banner.png)'),
    (rf'(?m)^# {LOADER}$', f'# {NAME}'),
]
RULES = [
    ('README.md', README_ONLY + PROSE),
    ('INSTALL.txt', PROSE),
    ('CONTRIBUTING.md', PROSE),
    ('docs/AUTHORING.md', PROSE),
    ('docs/MIGRATION_VALIDATION.md', PROSE),
    ('docs/TECHNICAL.md', PROSE),
    ('docs/THIRD_PARTY_REFERENCE.md', PROSE),
    ('examples/README.md', PROSE),
]

NOTE_START, NOTE_END = '<!-- mhga-note:start -->', '<!-- mhga-note:end -->'
NOTE = f"""{NOTE_START}
> **{SHORT}** is an unofficial fork of [Bingus Shared Loader]({UPSTREAM_URL}) by CowboyBingus ([Zero-Clause BSD](LICENSE)). It follows upstream daily and adds semantic-versioned releases, CI and an optional AI-assisted review of each release.
>
> This repository builds `{STEM}-vN.zip`. Nothing is published from it yet, so until then upstream's [`Bingus-Shared-Loader-vN.zip`]({UPSTREAM_URL}/releases/latest) is the same loader. The display name lives in [`branding.json`](branding.json) and is not part of the loader's identity: the `CowboyBingusModLoader` API, the manager GUID, and the log file name, log header and console prefix are fixed contracts with every mod and tool ([docs/IDENTITY.md](docs/IDENTITY.md)).
{NOTE_END}"""


def owned_files():
    out = []
    for pattern, _ in RULES:
        out += sorted(Path(p).relative_to(ROOT).as_posix() for p in glob.glob(str(ROOT / pattern)))
    return out


def rules_for(rel):
    return next((rules for pattern, rules in RULES if (ROOT / rel).as_posix() in glob.glob(str(ROOT / pattern))), [])


def apply_note(text):
    if NOTE_START in text and NOTE_END in text:
        return re.sub(re.escape(NOTE_START) + r'.*?' + re.escape(NOTE_END), lambda _: NOTE, text, count=1, flags=re.S)
    title = re.search(rf'(?m)^# {re.escape(NAME)}$', text)
    return text if not title else text[: title.end()] + '\n\n' + NOTE + text[title.end():]


def main():
    if '--list' in sys.argv:
        print('\n'.join(owned_files()))
        return 0
    check = '--check' in sys.argv
    changed = []
    for rel in owned_files():
        path = ROOT / rel
        text = path.read_bytes().decode('utf-8')
        new = text
        for pattern, repl in rules_for(rel):
            new = re.sub(pattern, repl, new)
        if rel == 'README.md':
            new = apply_note(new)
        if new != text:
            changed.append(rel)
            if not check:
                path.write_bytes(new.encode('utf-8'))
    for rel in changed:
        print(('would change: ' if check else 'rebranded: ') + rel)
    if not changed:
        print('branding already applied')
    return 1 if (check and changed) else 0


if __name__ == '__main__':
    sys.exit(main())
