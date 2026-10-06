"""Verify archived035 build evidence and preserve034/C44 source boundaries."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    raw=ROOT/"analysis/local-h1-firmware-035"
    prior=json.loads((ROOT/"analysis/h1-board-artifacts.json").read_text())
    count=0
    for group in ("sources","status_files","evidence"):
        for item in prior[group]:
            p=(raw/"baseline-status" if group=="status_files" else ROOT)/item["path"]
            assert p.stat().st_size==item["bytes"] and sha(p)==item["sha256"],item["path"]
            count+=1
    c44=json.loads((ROOT/"source-manifest.json").read_text())
    for item in c44["files"]:
        assert sha(ROOT/item["path"])==item["sha256"],item["path"]
    prep=json.loads((raw/"arm-final/h1-preparation.json").read_text())
    for name,digest in prep["files"].items():
        assert sha(raw/"arm-final/src"/name)==digest,name
        if name.startswith("nes_h1_"):
            assert sha(ROOT/"src/nes/firmware"/name)==digest,name
    fw=json.loads((raw/"arm-build.json").read_text())
    assert sha(raw/"arm-final/firmware-h1-035.stm")==fw["sha256"]
    assert (raw/"arm-final/firmware-h1-035.stm").stat().st_size==fw["bytes"]
    log=(raw/"build-02.log").read_text()
    assert "PASS: experimental H1 firmware "+fw["sha256"] in log
    assert "warning:" not in log and "error:" not in log
    dis=(raw/"arm-final/main-disassembly.txt").read_text()
    assert dis.count("<nes_h1_run>")==3 and dis.count("<nes_h1_is_marker>")==4
    host=json.loads((raw/"host-04/result.json").read_text())
    assert len(host["passed"])==11
    assert len([s for s in (raw/"host-04/test.log").read_text().splitlines() if s.startswith("PASS ")])==11
    assert (raw/"host-04/compile.log").stat().st_size==0
    io_log=(raw/"io-audit/audit.log").read_text()
    assert "0 errors, 0 warnings" in io_log
    assert (raw/"io-audit/board.sdc").read_bytes()==(ROOT/"analysis/local-h1-board-034/resource/board.sdc").read_bytes()
    rows=(raw/"io-audit/delays.tsv").read_text().splitlines()[1:]
    delays={line.split("\t")[0]:float(line.split("\t")[2]) for line in rows}
    assert len(delays)==6
    result={"candidate":"NES-H1-FIRMWARE-035","prior034_entries":count,
        "c44_source_hashes":len(c44["files"]),"arm_build":"PASS","arm_bytes":fw["bytes"],
        "arm_sha256":fw["sha256"],"arm_compile_warnings":0,"compiled_manual_entry_calls":3,
        "compiled_marker_checks":4,"host_cases":host["passed"],
        "io_delay_model":"Slow 1200mV 85C","io_group_longest_ns":delays,
        "unconstrained_input_ports":38,"unconstrained_output_ports":11,
        "hardware_executed":False,"hardware_eligible":False,
        "scope":"Full ARM build plus host GPIO/SPI mock; prior034 physical fit delay inventory only. No MCU hardware execution, IO signoff or GBC runtime regression."}
    (ROOT/"analysis/h1-firmware-verification.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
