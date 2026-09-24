#!/usr/bin/env python3
"""Validate `## First 10 clients` sections in business idea Markdown files.

Usage:
    python scripts/validate_first_10_clients.py /path/to/business_ideas/ideas
    python scripts/validate_first_10_clients.py /path/to/business_idea_generator/data/ideas

Checks each *.md file for:
- exactly one `## First 10 clients` section
- exactly 10 numbered linked entries
- at least 10 `Specific need:` fields
- at least 10 `How to contact:` fields
- at least 10 public Markdown links in the section
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def first_10_section(text: str) -> str:
    if "## First 10 clients" not in text:
        return ""
    section = text.split("## First 10 clients", 1)[1]
    next_heading = re.search(r"\n## [^#]", section)
    if next_heading:
        section = section[: next_heading.start()]
    return section


def validate_file(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    section_count = text.count("## First 10 clients")
    section = first_10_section(text)
    entries = len(re.findall(r"^\d+\.\s+(?:\*\*)?\[", section, re.MULTILINE))
    needs = len(re.findall(r"(?:\*\*)?Specific need(?:\*\*)?:", section))
    contacts = len(re.findall(r"(?:\*\*)?How to contact(?:\*\*)?:", section))
    links = len(re.findall(r"\[[^\]]+\]\(https?://[^)]+\)", section))

    ok = section_count == 1 and entries == 10 and needs >= 10 and contacts >= 10 and links >= 10
    detail = (
        f"sections={section_count} entries={entries} "
        f"specific_need={needs} how_to_contact={contacts} links={links}"
    )
    return ok, detail


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ideas_dir", type=Path, help="Directory containing idea Markdown files")
    args = parser.parse_args()

    files = sorted(args.ideas_dir.glob("*.md"))
    if not files:
        print(f"No Markdown files found in {args.ideas_dir}")
        return 2

    problems: list[str] = []
    for path in files:
        ok, detail = validate_file(path)
        if not ok:
            problems.append(f"{path.name}: {detail}")

    print(f"validated {len(files)} files in {args.ideas_dir}")
    if problems:
        print("Problems:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("All files have valid First 10 clients sections.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
