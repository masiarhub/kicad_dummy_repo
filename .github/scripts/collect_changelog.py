#!/usr/bin/env python3
"""Changelog fragments: one file per change in changelog.d/, merged into CHANGELOG.md at release.

Every feature PR adds a NEW file changelog.d/<feature>-<topic>.md instead of
editing CHANGELOG.md, so parallel PRs never conflict (GitHub's merge ignores
merge=union). A fragment uses Keep a Changelog headings:

    ### Added
    - 5V buck converter (TPS62130)

    ### Fixed
    - Swapped CAN_H / CAN_L labels

Usage (from the repo root):
    collect_changelog.py --check   validate fragments, change nothing (PR check)
    collect_changelog.py           move all fragments into "## [Unreleased]" of
                                   CHANGELOG.md and delete them (release tag job)
"""

import argparse
import os
import re
import sys
from pathlib import Path

TYPES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
HEADING = re.compile(r"^###\s+(.+?)\s*$")
BULLET = re.compile(r"^[-*]\s+(.*\S)\s*$")
CONTINUATION = re.compile(r"^\s{2,}(\S.*?)\s*$")


def parse_fragment(path):
    """Return ({type: [entry, ...]}, [error, ...]) for one fragment file."""
    entries, errors, section = {}, [], None
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        if m := HEADING.match(line):
            title = m.group(1).capitalize()
            if title not in TYPES:
                errors.append(f"{path}:{n}: unknown heading '### {m.group(1)}' (use one of: {', '.join(TYPES)})")
                section = None
            else:
                section = title
            continue
        if m := BULLET.match(line):
            if section is None:
                errors.append(f"{path}:{n}: bullet before a '### Added/Changed/...' heading")
                continue
            entries.setdefault(section, []).append(m.group(1))
            continue
        if (m := CONTINUATION.match(line)) and section and entries.get(section):
            entries[section][-1] += " " + m.group(1)
            continue
        errors.append(f"{path}:{n}: expected '### <Type>' or '- <text>', got: {line.strip()}")
    if not errors and not entries:
        errors.append(f"{path}: no entries")
    return entries, errors


def merge_into_changelog(changelog, collected):
    """Append the collected entries to the subsections of '## [Unreleased]'."""
    text = changelog.read_text(encoding="utf-8")
    head = re.search(r"^## \[Unreleased\][^\n]*\n", text, re.M)
    if not head:
        sys.exit(f"{changelog}: no '## [Unreleased]' section")
    end = re.compile(r"^(## \[|\[[^\]]+\]:)", re.M).search(text, head.end())
    end = end.start() if end else len(text)
    block = text[head.end():end]

    # Existing subsections of Unreleased, in file order
    preamble, sections, order, current = [], {}, [], None
    for line in block.splitlines():
        if m := HEADING.match(line):
            current = m.group(1).capitalize()
            if current not in sections:
                sections[current] = []
                order.append(current)
        elif current is None:
            preamble.append(line)
        elif line.strip():
            sections[current].append(line)

    bullet = "-   " if re.search(r"^-   \S", text, re.M) else "- "
    for kind in TYPES:
        if kind in collected:
            if kind not in sections:
                sections[kind] = []
                order.append(kind)
            sections[kind] += [bullet + e for e in collected[kind]]

    out = "\n".join(line for line in preamble if line.strip())
    out = (out + "\n\n") if out else "\n"
    for kind in order:
        out += f"### {kind}\n\n" + "".join(line + "\n" for line in sections[kind]) + "\n"
    changelog.write_text(text[:head.end()] + out + text[end:], encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="only validate the fragments")
    ap.add_argument("--dir", default="changelog.d", type=Path)
    ap.add_argument("--changelog", default="CHANGELOG.md", type=Path)
    args = ap.parse_args()

    fragments = sorted(p for p in args.dir.glob("*.md") if p.name.lower() != "readme.md")
    collected, errors = {}, []
    for path in fragments:
        entries, errs = parse_fragment(path)
        errors += errs
        for kind, items in entries.items():
            collected.setdefault(kind, []).extend(items)

    summary = [f"### Changelog fragments ({len(fragments)})", ""]
    summary += [f"- **{k}:** {e}" for k in TYPES for e in collected.get(k, [])] or ["_None._"]
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("\n".join(summary) + "\n")

    if errors:
        for e in errors:
            loc, _, msg = e.partition(": ")
            file, _, line = loc.partition(":")
            print(f"::error file={file},line={line or 1},title=Changelog fragment::{msg}" if os.environ.get("GITHUB_ACTIONS") else e)
        return 1
    print("\n".join(summary))
    if args.check or not fragments:
        return 0

    merge_into_changelog(args.changelog, collected)
    for path in fragments:
        path.unlink()
    print(f"Moved {len(fragments)} fragment(s) into {args.changelog} [Unreleased]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
