"""The loader's name is display-only: prove nothing functional depends on it.

Pure Python (no game files, no LuaJIT), so it runs anywhere:  python tests/test_branding.py
"""
import ast
import hashlib
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import branding  # noqa: E402
from package import package_release  # noqa: E402

# The identity contract: the manager GUID (gameplay packs list it in `requires`).
GUID = '612eaf70-d682-43c7-9efd-16dcc695f977'

# The loader's PROTOCOL. These look like names but are machine-matched strings: the first log line is parsed back by
# src/health.lua, compared by scripts/pin_tested.py and tests, and users, the pack's docs and other tools look for
# the file names. They are never computed from branding.json. See docs/IDENTITY.md.
PROTOCOL = {
    'src/shared_loader.lua': [
        r"local LOG_NAME = 'BingusSharedLoader\.log'",
        r"'Bingus Shared Loader loader-v\d+; API 1'",          # the log's first line
        r"'\[BingusSharedLoader\] '",                         # console prefix
        r"BingusSharedLoader-jit-guard\.off",                  # the user-facing kill-switch file
        r"CowboyBingusModLoader",                              # the global every mod looks up
    ],
    'src/health.lua': [r"\^Bingus Shared Loader \(loader%-v%d\+\)"],   # parses that first line back
}

# Code (not prose) must never spell a display name: it comes from branding.json.
CODE_FILES = ['scripts/build.py', 'scripts/package.py', 'scripts/build_addon.py', 'tests/test_package.py',
              'tests/test_overlay_compatibility.py', 'tests/test_shared_packages.py']


def brand(name, stem, short='MH'):
    return {'name': name, 'short_name': short, 'artifact_stem': stem}


class Validation(unittest.TestCase):
    def test_current_branding_is_valid(self):
        b = branding.load(ROOT)
        self.assertTrue(b['name'] and b['artifact_stem'] and b['short_name'] and b['pack']['name'])

    def test_rejects_unsafe_values(self):
        for bad in ({'name': "It's"}, {'name': 'a"b'}, {'name': 'a\\b'}, {'name': 'a\nb'}, {'name': ''},
                    {'name': ' padded '}, {'name': 'x' * 65}, {'artifact_stem': 'has space'},
                    {'artifact_stem': 'paren(s)'}, {'artifact_stem': '.hidden'}, {'artifact_stem': 'a/b'},
                    {'short_name': 'x' * 17}, {'icon': '../outside.png'}, {'icon': 'assets/../x.png'},
                    {'icon': '/abs/x.png'}, {'icon': 'assets/x.jpg'}, {'icon': 'other/x.png'}, {'icon': 5},
                    {'pack': {'name': "bad'name", 'artifact_stem': 'ok'}}, {'pack': {'name': 'ok', 'artifact_stem': 'a b'}}):
            with self.assertRaises(ValueError, msg=bad):
                branding.validate({**brand('Name', 'Stem'), **bad})

    def test_accepts_ordinary_values(self):
        branding.validate(brand('MHGA Shared Loader', 'MHGA-Shared-Loader'))
        branding.validate({**brand('A', 'A'), 'icon': 'assets/mhga/thumbnail.png',
                           'pack': {'name': 'Pack', 'artifact_stem': 'Pack', 'previous': [{'name': 'Old', 'artifact_stem': 'Old'}]}})


class IdentityAndProtocol(unittest.TestCase):
    def test_guid_is_a_pinned_plain_constant(self):
        tree = ast.parse((ROOT / 'scripts/build.py').read_text(encoding='utf-8'))
        found = {n.targets[0].id: n.value for n in tree.body
                 if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
        self.assertIsInstance(found['GUID'], ast.Constant, 'GUID must be a literal, not computed from anything')
        self.assertEqual(found['GUID'].value, GUID)
        self.assertFalse({n.id for n in ast.walk(found['GUID']) if isinstance(n, ast.Name)} & {'BRANDING'})
        self.assertIn("'guid': GUID", (ROOT / 'scripts/build.py').read_text(encoding='utf-8'))

    def test_protocol_strings_are_present_in_the_loader(self):
        for rel, patterns in PROTOCOL.items():
            text = (ROOT / rel).read_text(encoding='utf-8')
            for pattern in patterns:
                self.assertRegex(text, pattern, f'{rel} lost a protocol string: {pattern}')

    def test_health_parses_exactly_what_the_loader_writes(self):
        loader = (ROOT / 'src/shared_loader.lua').read_text(encoding='utf-8')
        health = (ROOT / 'src/health.lua').read_text(encoding='utf-8')
        written = re.search(r"'(Bingus Shared Loader) loader-v\d+; API 1'", loader).group(1)
        parsed = re.search(r"\^(Bingus Shared Loader) \(loader%-v%d\+\)", health).group(1)
        self.assertEqual(written, parsed)

    def test_no_display_name_literals_in_code(self):
        current = branding.load(ROOT)
        names = [current['name'], current['short_name'], current['artifact_stem'], current['pack']['name'],
                 current['pack']['artifact_stem']]
        names += [p[k] for p in current.get('previous', []) + current['pack'].get('previous', []) for k in ('name', 'artifact_stem')]
        for rel in CODE_FILES:
            text = (ROOT / rel).read_text(encoding='utf-8')
            for literal in names:
                self.assertNotIn(literal, text, f'{rel} spells the display name {literal!r}; read branding.json')
            self.assertIsNone(re.search(r'Bingus Shared Loader|Bingus-Shared-Loader|BingusSharedLoader-(?:README|manifest)'
                                        r'|Vanilla ?Plus ?Megapack|Vanilla-Plus-Megapack', text), rel)


class PackagingIndependence(unittest.TestCase):
    """Package the same build under two different brands: only names may differ."""

    def make(self, tmp, tag, b, icon=None):
        root, build = Path(tmp) / tag, Path(tmp) / (tag + '-build')
        (root / 'build').mkdir(parents=True)
        (root / 'assets/mhga').mkdir(parents=True)
        build.mkdir()
        (root / 'INSTALL.txt').write_bytes(b'install text\n')
        payload = bytes(range(256)) * 4
        (root / 'build/payload.bin').write_bytes(payload)
        report = {'name': b['name'], 'artifact_stem': b['artifact_stem'], 'revision': 'loader-v1', 'version': '1',
                  'guid': GUID, 'description': 'd', 'game_exe_sha256': '0' * 64, 'game_dll_sha256': '1' * 64,
                  'deployment_files': {'data/payload.bin': 'build/payload.bin'},
                  'files': {'build/payload.bin': hashlib.sha256(payload).hexdigest().upper()},
                  'provides': {'shared_loader_api': 1, 'addon_discovery': 1}}
        if icon:
            (root / 'assets/mhga/icon.png').write_bytes(icon)
            report['icon'] = 'assets/mhga/icon.png'
        release = package_release(root, build, report)
        return release, zipfile.ZipFile(release)

    def test_only_names_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            one, z1 = self.make(tmp, 'one', brand('Alpha Loader', 'Alpha'))
            two, z2 = self.make(tmp, 'two', brand('Omega Loader (v2)', 'Omega'))
            self.assertEqual((one.name, two.name), ('Alpha-v1.zip', 'Omega-v1.zip'))
            functional = {'manifest.json', 'data/payload.bin'}
            self.assertEqual(sorted(set(z1.namelist()) - functional), ['Alpha-README.txt', 'Alpha-manifest.json'])
            self.assertEqual(sorted(set(z2.namelist()) - functional), ['Omega-README.txt', 'Omega-manifest.json'])
            self.assertEqual(z1.read('data/payload.bin'), z2.read('data/payload.bin'))
            m1, m2 = json.loads(z1.read('manifest.json')), json.loads(z2.read('manifest.json'))
            self.assertEqual(m1['Guid'], m2['Guid'])
            self.assertEqual(m1['Description'], m2['Description'])
            self.assertEqual((m1['Name'], m2['Name']), ('Alpha Loader - v1', 'Omega Loader (v2) - v1'))
            self.assertEqual(m1['Options'][0]['Include'], m2['Options'][0]['Include'])
            p1, p2 = json.loads(z1.read('Alpha-manifest.json')), json.loads(z2.read('Omega-manifest.json'))
            for key in set(p1) | set(p2):
                if key in ('name', 'artifact_stem'):
                    continue
                if key == 'files':
                    self.assertEqual({k: v for k, v in p1[key].items() if k in functional},
                                     {k: v for k, v in p2[key].items() if k in functional})
                else:
                    self.assertEqual(p1.get(key), p2.get(key), key)

    def test_custom_icon_is_packaged_as_thumbnail(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, package = self.make(tmp, 'icon', brand('N', 'N'), icon=b'\x89PNG-icon-bytes')
            self.assertEqual(package.read('thumbnail.png'), b'\x89PNG-icon-bytes')
            self.assertEqual(json.loads(package.read('manifest.json'))['IconPath'], 'thumbnail.png')


class RebrandScope(unittest.TestCase):
    """The rebrand script may only edit prose, never code, tests or anything protocol."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / '.github/scripts'))
        import rebrand
        self.rebrand = rebrand

    def test_never_touches_code_or_tests(self):
        for rel in self.rebrand.owned_files():
            self.assertFalse(rel.startswith(('src/', 'tests/', 'scripts/')), f'{rel}: code must not be rebranded')
            self.assertFalse(rel.endswith(('.lua', '.py')), f'{rel}: no code file may be rebranded')

    def test_rules_leave_every_protocol_string_alone(self):
        sample = ('`BingusSharedLoader.log` [BingusSharedLoader] BingusSharedLoader-jit-guard.off CowboyBingusModLoader '
                  'Bingus Shared Loader loader-v20; API 1 mods/cowboybingus/vanilla_plus_megapack 612eaf70-d682-43c7-9efd-16dcc695f977')
        for _, rules in self.rebrand.RULES:
            text = sample
            for pattern, repl in rules:
                text = re.sub(pattern, repl, text)
            self.assertEqual(text, sample)


if __name__ == '__main__':
    unittest.main(verbosity=2)
