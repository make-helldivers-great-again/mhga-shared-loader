# Identity and protocol versus name

The loader has a **name** (what people read) and an **identity and protocol** (what software matches on). They
are separate on purpose, so renaming the loader never changes anything functional.

## Name: `branding.json`

The only place the display name lives. Nothing functional is derived from it.

| Field | Used for |
|---|---|
| `name` | the title in Arsenal / HD2MM, the build description, docs |
| `short_name` | prose |
| `artifact_stem` | file names only: `<stem>-vN.zip`, `<stem>-manifest.json`, `<stem>-README.txt` |
| `icon` | the box icon shown in the mod manager (a PNG under `assets/`); packaged as `thumbnail.png` |
| `pack` | display name and file stem of the gameplay pack the docs mention |
| `previous` | earlier brands, so docs that still use them can be rewritten |

Values are validated (`scripts/branding.py`), so a name can never break a string literal, JSON or a file name.

**To rename:** move the current values into `previous`, put the new ones in, run
`python .github/scripts/rebrand.py` (rewrites the prose), and rebuild. `tests/test_branding.py` proves the build
output differs only in those names.

## Identity and protocol: fixed contracts, never derived from a name

Several of these *look* like names. They are not: each is matched by machine, by other repositories, or by users.

| Contract | Value | Who depends on it |
|---|---|---|
| Runtime API global | `CowboyBingusModLoader` | every mod and the gameplay packs look it up (`rawget(_G, 'CowboyBingusModLoader')`) |
| API marker | `api = 1` | mods check it |
| Manager GUID | `612eaf70-d682-43c7-9efd-16dcc695f977` | Arsenal / HD2MM key the package on it; packs list it in `requires` |
| Owned resource | `core/wwise/lua/wwise_flow_callbacks` | the game's resource system |
| Log file | `BingusSharedLoader.log` | users and docs point at it; tests and the TestHarness read it |
| Log first line | `Bingus Shared Loader loader-vN; API 1` | **parsed back** by `src/health.lua` (previous-session summary), compared by `scripts/pin_tested.py` and the tests |
| Console prefix | `[BingusSharedLoader] ` | asserted by tests, grepped by users |
| Kill-switch file | `BingusSharedLoader-jit-guard.off` | users create it to switch the churn guard off |
| Log folder | `%LOCALAPPDATA%/CowboyBingus/Helldivers2` | shared with every CowboyBingus mod |

The log header is the clearest case: the loader writes its own display name as the first line of its log and later
parses that line back to recognise the previous session. If that string followed the display name, renaming the
loader would silently break the health report for everyone upgrading. So it is a protocol token that merely
resembles the original name, and it stays.

`tests/test_branding.py` enforces the separation: the GUID is a pinned plain constant that must not reference
branding, every protocol string must still be present in `src/`, `health.lua` must parse exactly what the loader
writes, code files must not spell any brand name, packaging one build under two brands may differ only in the name
fields and file names, and the rebrand rules may never touch a protocol string or any code file.

`tests/test_shared_packages.py` used to identify the loader package by its display name; it now uses the GUID.
