#!/usr/bin/env python3
"""Check repository entry points without tools, private inputs or hardware tests."""

import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ["목표", "작업내용", "성과", "후속작업"]
ENTRY_DOCS = [
    "README.md", "AGENTS.md", "CONTRIBUTING.md", "cores/README.md",
    "cores/nes/README.md", "cores/nes/HANDOFF.ko.md",
    "cores/nes/REPRODUCING.ko.md", "docs/README.md",
    "docs/PROJECT-STATUS.ko.md", "docs/development/RESUME.ko.md",
    "docs/development/MILESTONE-WORKFLOW.ko.md",
    "docs/progress/archive/README.md",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    progress = ROOT / "docs/progress"
    notes = sorted(progress.glob("pr-*.md"))
    paths = [ROOT / name for name in ENTRY_DOCS] + sorted(progress.glob("*.md"))
    links = 0
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            require(resolved.is_relative_to(ROOT), f"Link escapes repository: {path}: {target}")
            require(resolved.exists(), f"Missing link: {path.relative_to(ROOT)} -> {target}")
            links += 1
    for path in [ROOT / ".github/PULL_REQUEST_TEMPLATE.md"] + notes:
        headings = re.findall(r"^## (.+)$", path.read_text(encoding="utf-8"), re.M)
        require(headings == SECTIONS, f"Four-section format: {path.relative_to(ROOT)}")
    for name, limit in [("README.md", 100), ("AGENTS.md", 100),
                        ("cores/nes/HANDOFF.ko.md", 120)]:
        count = len((ROOT / name).read_text(encoding="utf-8").splitlines())
        require(count <= limit, f"Entry point grew to {count} lines: {name}; use progress records")

    archive = progress / "archive/2026-10-29"
    manifest = read_json(archive / "manifest.json")
    for row in manifest["files"]:
        data = (archive / row["archive_path"]).read_bytes()
        require(len(data) == row["bytes"], f"Archive size: {row['archive_path']}")
        require(hashlib.sha256(data).hexdigest() == row["sha256"],
                f"Archive SHA256: {row['archive_path']}")

    registry = read_json(ROOT / "cores/registry.json")
    original = read_json(archive / "core-registry.json")
    require({k: v for k, v in registry.items() if k != "cores"} ==
            {k: v for k, v in original.items() if k != "cores"}, "Board/product metadata changed")
    require([x for x in registry["cores"] if x["id"] != "nes"] ==
            [x for x in original["cores"] if x["id"] != "nes"], "GBC/PCE metadata changed")
    nes = next(x for x in registry["cores"] if x["id"] == "nes")
    for key in ["document", "handoff", "verification", "development_evidence", "plan",
                "reproduction_document", "status_document", "progress", "historical_registry"]:
        require((ROOT / nes[key]).is_file(), f"Registry link missing: {key}: {nes[key]}")
    measured = read_json(ROOT / nes["verification"])
    trial = re.search(r"\d+", str(measured["trial"])).group()
    require(nes["hardware_candidate"] == "NROM" + trial, "Hardware candidate/evidence mismatch")
    completed = sum(x["display"]["completed"] for x in measured["runs"])
    seconds = sum(x["display"]["seconds"] for x in measured["runs"])
    fps = f"{completed / seconds:.2f}"
    for name in ["README.md", "docs/PROJECT-STATUS.ko.md", "cores/nes/HANDOFF.ko.md"]:
        require(fps in (ROOT / name).read_text(encoding="utf-8"), f"Measured FPS absent: {name}")
    plan = read_json(ROOT / nes["plan"])
    if plan.get("execution_state", {}).get("performance_work") == "paused_by_user":
        require(nes["work_state"] == "performance_paused_by_user", "Pause state mismatch")
        for name in ["README.md", "AGENTS.md", "docs/development/RESUME.ko.md"]:
            require("중지" in (ROOT / name).read_text(encoding="utf-8"), f"Pause notice absent: {name}")

    index = read_json(progress / "pull-requests.json")
    numbers = [row["number"] for row in index["items"]]
    require(len(numbers) == len(set(numbers)), "Duplicate PR index entry")
    require(set(range(1, 135)).issubset(numbers), "Initial PR1-134 history lost")
    for row in index["items"]:
        for key in ["record", "original_snapshot"]:
            if row.get(key):
                require((progress / row[key]).is_file(), f"Missing PR {key}: {row['number']}")
    print(f"PASS: {len(paths)} entry documents, {links} local links, {len(notes)} PR formats")
    print(f"PASS: {len(manifest['files'])} byte/hash-preserved archives; GBC/PCE metadata unchanged")
    print(f"PASS: {nes['hardware_candidate']} measured {fps}fps, pause/registry/index consistent")
    print("Scope: documentation consistency only; no build, simulation or hardware test")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
