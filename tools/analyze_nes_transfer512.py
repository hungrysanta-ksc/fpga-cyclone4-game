# SPDX-License-Identifier: MIT
"""Verify the four runs and summarize the measured, nonphysical timing and whole-board costs."""
import argparse
import csv
import json
import re
from pathlib import Path
from statistics import mean
from analyze_nes_output511 import unpack_map
from nes_raw506 import sha

ROOT = Path(__file__).resolve().parents[1]
CLOCKS_PER_MS = 21477.272
SELECTED = {"original":"original04","map":"map04","input":"input03","both":"both03"}

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def logical_packets(folder):
    packets = []
    for line in (folder/"packets.jsonl").read_text().splitlines():
        _,_,hex_body,hex_tile=json.loads(line)
        p=bytes.fromhex(hex_body)
        assert len(p)==16+int.from_bytes(p[12:14],"little")
        # Compare the same independent oracle for every map address, identity and byte.
        if p[1]==2 and p[0] in (2,4,9):
            if p[0]==9:
                data=unpack_map(p[14:16]+p[16:])
            elif p[0]==4:
                data=p[16:]*(int.from_bytes(p[14:16],"little")//2)
            else:
                data=p[16:]
            p=b"\x02"+p[1:12]+len(data).to_bytes(2,"little")+b"\0\0"+data
        packets.append((p,hex_tile))
    for generation in range(905, 917):
        batch = [p for p,tile in packets if int.from_bytes(p[8:10],"little")==generation]
        assert batch[0][0]==1 and batch[-1][0]==3
        assert [int.from_bytes(p[2:4],"little") for p in batch]==list(range(len(batch)))
    return packets


def equivalent_packets(packets):
    # Both lanes share sequence numbers. A legal change of arbitration can
    # reorder bulk relative to ordinary; compare each ordered lane separately.
    return [[(p[:2]+p[4:],tile) for p,tile in packets if (p[0]==7)==bulk] for bulk in (False,True)]

def fpga(folder):
    summary=(folder/"output_files/board.fit.summary").read_text()
    assert "Fitter Status : Successful" in summary
    fields={}
    for key,label in [("LE","Total logic elements"),("comb","Total combinational functions"),("FF","Dedicated logic registers"),("RAM_bits","Total memory bits")]:
        fields[key]=int(re.search(re.escape(label)+r"\s*:\s*([\d,]+)",summary)[1].replace(",",""))
    fit=(folder/"output_files/board.fit.rpt").read_bytes().decode("latin1")
    fields["M9K"]=int(re.search(r"; M9Ks\s*;\s*(\d+) /",fit)[1])
    for view in ("implementation","nominal"):
        path=folder/(view+"-paths204.tsv")
        with path.open() as f:
            paths=[r for r in csv.DictReader(f,delimiter="\t") if (r["from_clock"]=="nes")==(r["to_clock"]=="nes")]
        for check in ("setup","hold"):
            worst=min((r for r in paths if r["kind"]==check),key=lambda r:float(r["slack"]))
            fields[view+"_"+check+"_ns"]=float(worst["slack"])
            if view=="implementation" and check=="setup":
                fields["setup_endpoints"]=[worst["from"],worst["to"]]
    fields["report_SHA256"]={name:sha(folder/name) for name in (
        "output_files/board.fit.summary","output_files/board.fit.rpt",
        "implementation-paths204.tsv","nominal-paths204.tsv",
        "nes_native_spi165.sv","sink-program.hex")}
    return fields

def check(a):
    original=read(a.temp/"nes-transfer512-original04/joint.json")
    reference=a.temp/"nes-transfer512-original04"
    oracle=logical_packets(reference)
    result={}
    for mode,run in SELECTED.items():
        d=a.temp/("nes-transfer512-"+run)
        j=read(d/"joint.json")
        assert j["passed"] and j["parameters"]==original["parameters"] and j["commits"]==12
        assert j["vram_DMA_B"]==36144 and j["ROM_read_allocations"]==3280 and j["last_status"]==1
        assert j["future_ACK_filtered"] and j["max_bulk_banks"]<=2 and equivalent_packets(logical_packets(d))==equivalent_packets(oracle)
        frames=j["frames"]
        assert [f["generation"] for f in frames]==list(range(905,917))
        for f in frames:
            rgb=f"frame-{f['generation']}.rgb"
            assert sha(d/rgb)==sha(reference/rgb),rgb
        times=[f["ACK_masterclock"] for f in frames]
        later=[(b-c)/CLOCKS_PER_MS for c,b in zip(times[1:],times[2:])]
        events=read(d/"events.json")
        # Bind every observed D1 length to the serial RTL transaction for that variant.
        spi=a.temp/("nes-transfer512-spi01" if mode in ("input","both") else "nes-transfer512-spilegacy01")
        assert read(spi/"result.json")["passed"]
        for g in range(905,917):
            lengths=[int(line.split()[0]) for line in (spi/f"transactions-{g}.txt").read_text().splitlines() if line.split()[1].startswith("d1")]
            assert [e["bytes"] for e in events if e.get("opcode")=="0xd1" and e["generation"]==g]==lengths
        assert sum(e.get("opcode")=="0xea" for e in events)==12
        fw = (ROOT.parent/"probes/nes-service509/ARM03" if mode=="original" else a.probe/("ARM-"+mode+("-02" if mode=="input" else "-03")))
        firmware=fw/"src/obj-nes-100/firmware.stm"
        assert sha(firmware)==j["firmware_SHA256"]
        size=(fw/"size.log").read_text().splitlines()[-1].split()
        board=a.temp/("nes-fault507-board01" if mode=="original" else "nes-transfer512-fit-"+mode+"-01")
        client=(a.probe/"build03/client" if mode in ("map","both") else ROOT.parent/"probes/nes-output489/client04")
        assert sha(client/"sink-program.hex")==sha(board/"sink-program.hex")
        arm_wire=j["wire_B"]
        late_wire=sum(e["bytes"] if e["event"]=="SPI" else 8 for e in events if e["generation"]>=907 and e["event"] in ("observer","SPI"))
        result[mode]=dict(first_display_ms=(times[0]-j["parameters"]["start"])/CLOCKS_PER_MS,
                          second_gap_ms=(times[1]-times[0])/CLOCKS_PER_MS,later10_ms=sum(later),later_mean_ms=mean(later),
                          later_min_ms=min(later),later_max_ms=max(later),later_intervals_ms=later,ACK_clocks=times,
                          wire_B=sum(arm_wire.values()),nonquery_B=sum(v for k,v in arm_wire.items() if k not in ("0xd0","0xe0","0xe8")),
                          later_wire_B=late_wire,wire_by_op=arm_wire,firmware_B=firmware.stat().st_size,Flash_free_B=0x34000-firmware.stat().st_size,
                          BSS_B=int(size[2]),data_B=int(size[1]),ARM_observed_stack_gap_B=int(j["observed_stack_low"],16)-int(j["workspace_end"],16),
                          SNES_body_B=read(client/"build.json")["body_bytes"],SNES_stack_B=j["observed_stack_B"],SNES_new_scratch_B=10 if mode in ("map","both") else 0,
                          IRQ=j["SysTick_calls"],ARM_instructions=j["ARM_instructions"],ROM_reads=j["ROM_read_allocations"],
                          FPGA=fpga(board),joint_SHA256=sha(d/"joint.json"),events_SHA256=sha(d/"events.json"),firmware_SHA256=sha(firmware),
                          normalized_packet_count=len(oracle),RGB_equal=True)
    for r in result.values():
        r["later_delta_ms"]=r["later10_ms"]-result["original"]["later10_ms"]
        r["wire_delta_B"]=r["wire_B"]-result["original"]["wire_B"]
    guards=read(a.temp/"nes-transfer512-guards01/result.json")
    assert guards["passed"] and len(guards["cases"])==11
    arm=read(a.probe/"armguard01.json")
    assert arm["passed"] and arm["firmware_SHA256"]==result["both"]["firmware_SHA256"]
    cleanup={}
    for fault in ("none","program","done","busy","token"):
        row=read(a.probe/("cleanup03" if fault=="none" else "cleanup03-"+fault)/"result.json")
        assert row["passed"] and row["firmware_sha256"]==arm["firmware_SHA256"]
        cleanup[fault]=row["safe_return"]
    pairs=read(a.temp/"nes-transfer512-pairs01/result.json")
    assert pairs["passed"] and pairs["client_SHA256"]==guards["client_SHA256"]
    return dict(experiment=512,PR=141,physical_baseline="MMC509",physical_FPS=12.81624500665779,
                scope="One matched 905..916 sequence, actual linked ARM/65816, real RTL D1 transcripts, modeled SPI/IRQ/ROM timing; no new board run.",
                schedule=original["parameters"],variants=result,SNES_guards=guards,ARM_guards=arm,base_only_cleanup_safe_return=cleanup,
                paired_map_packet_clocks=pairs["packet_clocks"],
                physical_menu_test_on_candidates=False,full_CDC_IO_STA_approved=False,
                decision="Keep physical MMC509. Compare time and setup before delivery; map includes Flash recovery by sharing CRC routines and post-STOP formatting.")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("temp","probe","out"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    r=check(a)
    with a.out.open("x",encoding="utf8",newline="\n") as f:
        json.dump(r,f,indent=2);f.write("\n")
    print({k:(round(v["later10_ms"],4),v["wire_B"],v["Flash_free_B"],v["FPGA"]["implementation_setup_ns"]) for k,v in r["variants"].items()})
