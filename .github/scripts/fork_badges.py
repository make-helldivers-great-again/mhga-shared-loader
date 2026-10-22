#!/usr/bin/env python3
"""Regenerate the fork/release badge table at the top of README.md.

Lists the upstream repo plus every fork of it, with each one's latest release
tag + date and last push, newest release first. Anything released in the last
48 hours is flagged. Only the block between the markers is rewritten.
stdlib only; uses GITHUB_TOKEN if present (rate limits).
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

UPSTREAM = os.environ.get("UPSTREAM", "CowboyBingus/BingusSharedLoader")
README = os.environ.get("README", "README.md")
START, END = "<!-- forks:start -->", "<!-- forks:end -->"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json", **({"Authorization": "Bearer " + TOKEN} if TOKEN else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError:
        return None


def all_forks():
    out, page = [], 1
    while True:
        chunk = api(f"/repos/{UPSTREAM}/forks?per_page=100&page={page}") or []
        out += chunk
        if len(chunk) < 100:
            return out
        page += 1


def parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if ts else None


def esc(s):  # shields.io static-badge escaping
    return urllib.parse.quote(s.replace("-", "--").replace("_", "__").replace(" ", "_"), safe="_")


def badge(label, message, color):
    return f"![{label}: {message}](https://img.shields.io/badge/{esc(label)}-{esc(message)}-{color})"


def main():
    now = datetime.now(timezone.utc)
    repos = [api(f"/repos/{UPSTREAM}")] + all_forks()
    rows = []
    for r in repos:
        if not r:
            continue
        all_rels = [x for x in (api(f"/repos/{r['full_name']}/releases?per_page=20") or []) if not x.get("draft")]
        # upstream-sync.yml mirrors upstream's release notes onto the fork stamped with the
        # mirroring time; those are copies, not this repo's own releases, so skip them.
        rels = [x for x in all_rels if "Mirrored from https://github.com/" not in (x.get("body") or "")]
        mirrors = len(all_rels) - len(rels)
        rel = rels[0] if rels else None
        rdate = parse(rel["published_at"]) if rel else None
        rows.append((rdate, parse(r["pushed_at"]), r, rel, mirrors))
    if not rows:  # API unreachable/rate-limited: keep the existing table instead of writing an empty one
        print("no repository data; README left unchanged")
        return 0
    floor = datetime.min.replace(tzinfo=timezone.utc)
    rows.sort(key=lambda t: (t[0] or floor, t[1] or floor), reverse=True)

    lines = [START, "", f"**Forks of [{UPSTREAM}](https://github.com/{UPSTREAM}) and their latest releases** (auto-updated daily)", "",
             "| Repo | Latest release | Released | Last push |", "|---|---|---|---|"]
    for rdate, pushed, r, rel, mirrors in rows:
        fresh = rdate and (now - rdate).total_seconds() < 48 * 3600
        tag = badge("release", rel["tag_name"], "brightgreen" if fresh else "blue") if rel else badge("release", "mirrors upstream" if mirrors else "none", "lightgrey")
        when = badge("released", f"{rdate:%Y-%m-%d}", "brightgreen" if fresh else "blue") if rdate else badge("released", "never", "lightgrey")
        push = badge("pushed", f"{pushed:%Y-%m-%d}", "informational") if pushed else ""
        mark = " (upstream)" if r["full_name"] == UPSTREAM else (" (this fork)" if r["full_name"] == os.environ.get("GITHUB_REPOSITORY") else "")
        lines.append(f"| [{r['full_name']}]({r['html_url']}){mark}{' 🆕' if fresh else ''} | {tag} | {when} | {push} |")
    lines += ["", END]
    block = "\n".join(lines)

    text = open(README, encoding="utf-8").read()
    if START in text and END in text:
        head, rest = text.split(START, 1)
        text = head + block + rest.split(END, 1)[1]
    else:
        text = block + "\n\n" + text
    open(README, "w", encoding="utf-8").write(text)
    print(f"wrote {len(rows)} rows")


if __name__ == "__main__":
    sys.exit(main())
