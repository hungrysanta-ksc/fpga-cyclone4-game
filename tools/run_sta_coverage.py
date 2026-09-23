"""Rebuild one frozen Quartus candidate privately to audit timing coverage.

The candidate's fitted placement uses its recorded fitter-only SDC. Signoff
restores the original SDC. No bitstream is generated and no raw report is
copied into the public repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


CANDIDATE = "probes/full-core-link/results/fxpak-g13-prefill-endpoint-seed7-hold1-v1"
OUTPUT = "probes/full-core-link/results/p0-g13-sta-coverage-v1"
COPY_SUFFIXES = {".sv", ".v", ".vhd", ".vh", ".qsf", ".qpf", ".sdc", ".tcl"}
EXTRA_REPORTS = ("clock_checks.tcl", "cdc_metastability.tcl", "sta_endpoint_audit.tcl")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument(
        "--quartus-bin", type=Path,
        default=Path("C:/altera_lite/25.1std/quartus/bin64"),
    )
    args = parser.parse_args()
    snapshot = args.snapshot.resolve(strict=True)
    candidate = (snapshot / CANDIDATE).resolve(strict=True)
    output = (snapshot / OUTPUT).resolve()
    repository = Path(__file__).resolve().parent.parent
    if not candidate.is_relative_to(snapshot) or not output.is_relative_to(snapshot):
        raise ValueError("Candidate and output must be inside the private snapshot")
    if output.is_relative_to(repository) or output.exists():
        raise ValueError("Output must be a new private directory")

    evidence = json.loads((candidate / "verification.json").read_text(encoding="utf-8"))
    if not evidence.get("completed") or evidence.get("seed") != 7:
        raise ValueError("Expected completed frozen seed-7 candidate")
    for name, expected in evidence["source_sha256"].items():
        actual = sha256(candidate / name)
        if actual != expected:
            raise ValueError(f"Frozen input hash mismatch: {name}")
    for name in ("pin.qpf", "placement-target.sdc", *EXTRA_REPORTS[:2]):
        if not (candidate / name).is_file():
            raise FileNotFoundError(candidate / name)
    for tool in ("quartus_map", "quartus_fit", "quartus_sta"):
        if not (args.quartus_bin / f"{tool}.exe").is_file():
            raise FileNotFoundError(args.quartus_bin / f"{tool}.exe")

    output.mkdir(parents=True)
    for source in candidate.iterdir():
        if source.is_file() and source.suffix in COPY_SUFFIXES:
            shutil.copy2(source, output / source.name)
    shutil.copy2(repository / "tools" / "sta_endpoint_audit.tcl", output / "sta_endpoint_audit.tcl")
    boot = output / "BootROMs" / "cgb_boot.mif"
    boot.parent.mkdir()
    shutil.copy2(candidate / "BootROMs" / "cgb_boot.mif", boot)
    original_sdc = (output / "board_output_cdc.sdc").read_bytes()
    fitted_sdc = (output / "placement-target.sdc").read_bytes()
    result = {
        "candidate_id": candidate.name,
        "input_sha256": evidence["source_sha256"],
        "fitter_only_sdc_sha256": sha256(candidate / "placement-target.sdc"),
        "signoff_sdc_restored": False,
        "bitstream_generated": False,
        "stages": {},
        "status": "running",
    }
    manifest = output / "audit.json"

    def run(tool: str, *arguments: str) -> None:
        command = [str(args.quartus_bin / f"{tool}.exe"), *arguments]
        log = output / f"audit-{tool}-{'-'.join(arguments).replace('.', '_')}.log"
        with log.open("wb") as stream:
            completed = subprocess.run(
                command, cwd=output, stdout=stream, stderr=subprocess.STDOUT,
                timeout=1800, check=False,
            )
        result["stages"][log.name] = completed.returncode
        manifest.write_text(json.dumps(result, indent=2), encoding="utf-8")
        if completed.returncode:
            raise RuntimeError(f"{tool} exited {completed.returncode}; inspect {log.name}")

    try:
        (output / "board_output_cdc.sdc").write_bytes(fitted_sdc)
        run("quartus_map", "pin")
        run("quartus_fit", "pin")
        (output / "board_output_cdc.sdc").write_bytes(original_sdc)
        result["signoff_sdc_restored"] = True
        run("quartus_sta", "pin")
        for script in EXTRA_REPORTS:
            run("quartus_sta", "-t", script)
        result["status"] = "reports_generated"
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        raise
    finally:
        (output / "board_output_cdc.sdc").write_bytes(original_sdc)
        manifest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "stages": result["stages"]}))


if __name__ == "__main__":
    main()
