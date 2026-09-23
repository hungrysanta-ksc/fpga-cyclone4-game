"""Read archived Quartus reports; never equate constrained slack with board signoff.

Prints a JSON inventory. It does not run tools, edit constraints, grant waivers,
or issue a pass for shipping. Unknown/missing sections fail closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unittest


def parse_reports(summary, sta, fit_summary, fit):
    categories = ("Setup", "Hold", "Recovery", "Removal", "Minimum Pulse Width")
    records = re.findall(r"Type\s*:\s*([^\r\n]+)\s+Slack\s*:\s*([-+\d.]+)", summary)
    slacks = {c: [float(v) for label, v in records if c.lower() in label.lower()]
              for c in categories}
    # Quartus versions may spell the last type as 'Minimum Pulse Width'.
    missing = [c for c, values in slacks.items() if not values]
    counts = {}
    for label in ("Illegal Clocks", "Unconstrained Clocks", "Unconstrained Input Ports",
                  "Unconstrained Input Port Paths", "Unconstrained Output Ports",
                  "Unconstrained Output Port Paths"):
        match = re.search(r";\s*" + re.escape(label) + r"\s*;\s*(\d+)\s*;\s*(\d+)", sta)
        counts[label] = {"setup": int(match[1]), "hold": int(match[2])} if match else None
    resource_labels = {"logic_elements": (fit_summary, r"Total logic elements\s*:\s*([\d,]+)\s*/\s*([\d,]+)"),
                       "memory_bits": (fit_summary, r"Total memory bits\s*:\s*([\d,]+)\s*/\s*([\d,]+)"),
                       "m9k_blocks": (fit, r";\s*M9Ks\s*;\s*([\d,]+)\s*/\s*([\d,]+)")}
    resources = {}
    for name, (source, pattern) in resource_labels.items():
        match = re.search(pattern, source)
        if match:
            used, total = (int(x.replace(",", "")) for x in match.groups())
            resources[name] = {"used": used, "total": total, "remaining": total - used}
        else:
            resources[name] = None
    fractions = sorted(set(float(x) for x in re.findall(
        r"Fraction of Chains for which MTBFs Could Not be Calculated:\s*([\d.]+)", sta)))
    warnings = sorted(set(re.findall(r"Warning\s*\((\d+)\)", sta)))
    unresolved = []
    if missing:
        unresolved.append("Missing timing summary categories: " + ", ".join(missing))
    if any(v is None for v in counts.values()):
        unresolved.append("Missing timing coverage summary entries")
    if any(v and any(v.values()) for v in counts.values()):
        unresolved.append("Nonzero check_timing counts require endpoint classification; not automatically defects")
    if not fractions or any(x > 0 for x in fractions):
        unresolved.append("MTBF coverage incomplete or unreported; chain-by-chain review required")
    if warnings:
        unresolved.append("STA warnings require explicit classification")
    if any(x is None for x in resources.values()):
        unresolved.append("Resource report incomplete")
    unresolved.extend(["External board timing and CDC/reset protocol correctness are not certified by this parser",
                       "No physical functional qualification or waiver approval supplied"])
    return {
        "constrained_slack_pass": not missing and all(min(v) >= 0 for v in slacks.values()),
        "minimum_slack_ns": {c: min(v) if v else None for c, v in slacks.items()},
        "missing_timing_categories": missing,
        "check_timing_raw_summary": counts,
        "mtbf_unavailable_fractions": fractions,
        "sta_warning_ids": warnings,
        "resources": resources,
        "design_signoff": False,
        "shipping_ready": False,
        "review_required": unresolved,
    }


class ParserTests(unittest.TestCase):
    def fixture(self):
        return "\n".join(f"Type : Slow {x} 'sys'\nSlack : 0.1" for x in
                         ("Setup", "Hold", "Recovery", "Removal", "Minimum Pulse Width"))

    def test_positive_slack_never_certifies_board(self):
        result = parse_reports(self.fixture(), "", "", "")
        self.assertTrue(result["constrained_slack_pass"])
        self.assertFalse(result["design_signoff"])
        self.assertTrue(result["review_required"])

    def test_negative_slack(self):
        result = parse_reports(self.fixture().replace("Slack : 0.1", "Slack : -0.2", 1), "", "", "")
        self.assertFalse(result["constrained_slack_pass"])

    def test_missing_summary_fails_closed(self):
        self.assertFalse(parse_reports("", "", "", "")["constrained_slack_pass"])

    def test_counts_and_blocks(self):
        result = parse_reports(self.fixture(),
            "; Unconstrained Input Ports ; 36 ; 36 ;\nFraction of Chains for which MTBFs Could Not be Calculated: 0.962",
            "Total logic elements : 14,877 / 15,408\nTotal memory bits : 431,104 / 516,096",
            "; M9Ks ; 56 / 56 (100 %) ;")
        self.assertEqual(result["resources"]["m9k_blocks"]["remaining"], 0)
        self.assertEqual(result["resources"]["logic_elements"]["remaining"], 531)
        self.assertEqual(result["check_timing_raw_summary"]["Unconstrained Input Ports"]["hold"], 36)
        self.assertEqual(result["mtbf_unavailable_fractions"], [0.962])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(ParserTests)
        raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    if not args.candidate:
        parser.error("candidate report directory required")
    names = ("pin.sta.summary", "pin.sta.rpt", "pin.fit.summary", "pin.fit.rpt")
    raw = {name: (args.candidate / name).read_bytes() for name in names}
    result = parse_reports(*(raw[name].decode("utf-8", errors="replace") for name in names))
    result["candidate"] = str(args.candidate.resolve())
    result["report_sha256"] = {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()}
    print(json.dumps(result, ensure_ascii=False, indent=2))
