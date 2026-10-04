"""Summarize private Quartus UCP/MTBF reports without copying raw reports."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def table_rows(section: str, title: str) -> list[tuple[str, str, str]]:
    waiting = False
    active = False
    rows = []
    for line in section.splitlines():
        if re.fullmatch(rf"; {re.escape(title)}\s*;", line):
            waiting = True
            active = False
            continue
        if waiting and line.startswith("; From"):
            active = True
            continue
        if active and line.startswith("+"):
            if rows:
                break
            continue
        if active and line.startswith(";"):
            fields = tuple(part.strip() for part in line.split(";")[1:-1])
            if len(fields) != 3:
                raise ValueError(f"Unexpected report row: {line}")
            rows.append(fields)
    if not rows:
        raise ValueError(f"Missing report table: {title}")
    return rows


def property_value(section: str, name: str) -> str:
    match = re.search(rf"^; {re.escape(name)}\s*;\s*([^;]*?)\s*;", section, re.M)
    if not match:
        raise ValueError(f"Missing chain field: {name}")
    return match.group(1)


def family(port: str) -> str:
    return re.sub(r"\[\d+\]$", "", port)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_dir", type=Path)
    args = parser.parse_args()
    directory = args.audit_dir.resolve(strict=True)
    audit = json.loads((directory / "audit.json").read_text(encoding="utf-8"))
    if audit["status"] != "reports_generated" or not audit["signoff_sdc_restored"]:
        raise ValueError("Audit did not complete under the original signoff SDC")
    ucp = (directory / "full-unconstrained.rpt").read_text(encoding="utf-8")
    setup, hold = ucp.split("; Hold Analysis ;", 1)
    data = {}
    for kind, section in (("setup", setup), ("hold", hold)):
        incoming = table_rows(section, "Unconstrained Input Port Paths")
        outgoing = table_rows(section, "Unconstrained Output Port Paths")
        data[kind] = {
            "input_paths": len(incoming),
            "output_paths": len(outgoing),
            "input_port_families": dict(sorted(Counter(family(row[0]) for row in incoming).items())),
            "output_port_families": dict(sorted(Counter(family(row[1]) for row in outgoing).items())),
            "input_ports": sorted({row[0] for row in incoming}),
            "output_ports": sorted({row[1] for row in outgoing}),
            "input_to_output_no_clock": sum(not row[2] for row in incoming),
            "output_from_no_clock": sum(not row[2] for row in outgoing),
        }
    if data["setup"] != data["hold"]:
        raise ValueError("Setup and hold UCP tables disagree")

    mtbf = (directory / "cdc-metastability-8_slow_1200mv_85c.rpt").read_text(encoding="utf-8")
    chain_matches = re.findall(
        r"(?ms)^Synchronizer Chain #(\d+): (.*?)\n(.*?)(?=^Synchronizer Chain #|\Z)", mtbf
    )
    chains = []
    for number, status, body in chain_matches:
        chains.append({
            "number": int(number),
            "status": status,
            "source": property_value(body, "Source Node"),
            "synchronization_node": property_value(body, "Synchronization Node"),
            "identification": property_value(body, "Method of Synchronizer Identification"),
            "settling_ns": property_value(body, "Available Settling Time (ns)"),
            "source_clock_unknown": bool(re.search(r"^;  Unknown\s*;", body, re.M)),
        })
    if len(chains) != 53 or {chain["number"] for chain in chains} != set(range(1, 54)):
        raise ValueError("Expected all 53 synchronizer chains")
    result = {
        "candidate_id": audit["candidate_id"],
        "ucp": data["setup"],
        "mtbf": {
            "chains": len(chains),
            "not_calculated": sum("Not Calculated" in item["status"] for item in chains),
            "source_clock_unknown": sum(item["source_clock_unknown"] for item in chains),
            "identification": dict(Counter(item["identification"] for item in chains)),
            "calculated": [item for item in chains if "Not Calculated" not in item["status"]],
            "not_calculated_examples": [item for item in chains if "Not Calculated" in item["status"]][:5],
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
