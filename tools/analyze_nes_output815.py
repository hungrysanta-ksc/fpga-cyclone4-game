"""Compare workload-balanced physical bins and fixed-input 813 output schedules."""
import argparse
import csv
from itertools import combinations
import json
from pathlib import Path

import numpy as np

from analyze_nes_hardware663 import work
from analyze_nes_order810 import schedule, ms
from analyze_nes_output768 import csv_groups, fields, one, read, sha, timeline, waits
from analyze_nes_tail735 import section5

ROOT = Path(__file__).resolve().parents[1]
PROBES = ROOT.parent / "probes"
WORK = ("mapdirty","obj","bg")


def balance(sets):
    # Closest pair of nonnegative bin mixtures to the two original frame
    # distributions (Pearson distance). Enumerate the small set of active
    # bounds; stationarity, feasibility and complementary slackness certify
    # the minimum. No display times enter the choice of weights.
    prior, columns = [], []
    for index, rows in enumerate(sets):
        count = sum(r["frames"] for r in rows)
        for r in rows:
            prior.append(r["frames"]/count)
            sign = 1 if index == 0 else -1
            columns.append([1-index,index,*[sign*r[k]/r["frames"] for k in WORK]])
    p = np.array(prior)
    x = np.array(columns).T / np.array([[1],[1],[10],[50],[500]])
    target = np.array([1,1,0,0,0])
    for size in range(len(p)-len(target)+1):
        for excluded in combinations(range(len(p)),size):
            use = np.ones(len(p),dtype=bool)
            use[list(excluded)] = False
            m = x[:,use]
            q = p[use]
            try:
                dual = np.linalg.solve((m*q) @ m.T,m @ q-target)
            except np.linalg.LinAlgError:
                continue
            w = p*(1-x.T @ dual)
            if np.all(w[use]>=0) and np.all(w[~use]<=0):
                w[~use] = 0
                np.testing.assert_allclose(x @ w,target,atol=1e-11)
                return np.split(w,[len(sets[0])])
    raise ValueError("No common workload in the observed bins")


def physical(downloads):
    sets, pins, costs = [], {}, {}
    for edition, suffix in ((807,""),(813," (1)")):
        path = downloads/f"nes-budget-mmc{edition}{suffix}.txt"
        expected = read(ROOT/"analysis/hardware814-results.json")["runs"][f"MMC{edition}"]
        pins[path.name] = sha(path)
        assert pins[path.name] == expected["sha256"][path.name]
        b = fields(path.read_text(encoding="utf-8-sig"))
        assert (b["tick_ms"],b["bin_ticks"],b["bin_basis"]) == ("10","500","FRAME_START_NOT_SCENE")
        assert b["cost_op_order"].split(",")[4:7] == ["E0","E1","E8"]
        costs[edition] = {}
        for op, index in (("E0",4),("E8",6)):
            calls, size, hi, lo, _ = map(int,b[f"cost_op_{index:02}"].split(","))
            assert size==20*calls
            costs[edition][op] = ((hi<<32)+lo)*1000/(int(b["cost_clock_hz"])*calls)
        rows = work(b)[0][1:8]
        sets.append(rows)
    pairs = sum(all(abs(b[k]/b["frames"]-a[k]/a["frames"]) <= 0.20*a[k]/a["frames"] for k in WORK)
                for a in sets[0] for b in sets[1])
    result = dict(sha256=pins,cross_time_pairs_within_20pct=int(pairs),bins_examined=49)
    for edition,rows,weights in zip((807,813),sets,balance(sets),strict=True):
        start_weights = np.array([r["frames"] for r in rows],float)
        start_weights /= start_weights.sum()
        def means(w):
            keys = (*WORK,"seal","e0","e1","e8","plans","out")
            values = {k:sum(q*r[k]/r["frames"] for q,r in zip(w,rows,strict=True)) for k in keys}
            values["output_final_ack_ms"] = 10*values.pop("seal")
            values["E0_queries_per_frame"] = values.pop("e0")/20
            values["E8_queries_per_frame"] = values.pop("e8")/20
            return values
        result[edition] = dict(balanced=means(weights),observed=means(start_weights),
                               balanced_bin_weights=weights.tolist(),bins=rows,
                               whole_session_query_ms=costs[edition])
    return result


def detail(folder, gens):
    cpu = csv_groups(folder/"window.csv")
    events = read(folder/"events.json")
    packets = [json.loads(line) for line in (folder/"packets.jsonl").read_text().splitlines()]
    result = {}
    for g in gens:
        t = timeline(folder,g,cpu,events,packets)
        result[g] = {k:t[k] for k in ("work","output_ms","terms_ms","post_SEAL_DMA_bytes",
                                      "wire_before_SEAL_ms","display_interval_VB","final_waits","reveal_line")}
        seal = [r for r in cpu[g] if r["op"]==3]
        result[g]["check_and_wait_lines"] = [(r["event"],r["line"]) for r in seal
                                              if r["event"] in ("final212","wait169")]
        final = one(seal,"final212")["clock"]
        before = [resume for enter,resume in waits(seal) if resume<=final]
        if before:
            result[g]["last_upload_resume_to_check_ms"] = ms(final-before[-1])
            result[g]["bytes_after_last_upload_resume"] = sum(r["value"] for r in seal
                          if r["event"]=="ppu_dma" and before[-1]<=r["clock"]<final)
    return result


def replay(temp, case, phase, reference, base_dir, client):
    d = temp/f"nes-output809-{case}-p{phase}"
    r = schedule(d,reference,sha(client/"sink165.sfc"))
    assert section5(d)==section5(base_dir)
    for g in range(905,971):
        for template in ("frame-{}.rgb","expected-{}.bin","map-{}.bin"):
            f = template.format(g)
            assert (base_dir/f).read_bytes()==(d/f).read_bytes(),(case,phase,g,f)
    keys = ("firmware","commits","rgb_map_checked","early951","restored951","line951","display959",
            "intervals","dense_vblank","dense_ms","last_ACK","E0_polls","total_bus_B","hashes")
    dense = detail(d,range(952,971))
    costs = {k:sum(row["terms_ms"][k] for row in dense.values())/len(dense)
             for k in dense[952]["terms_ms"]}
    def raw_transfers(folder):
        with (folder/"seal528.csv").open() as f:
            return [(int(v["g"]),int(v["bank"]),int(v["src"]),int(v["dst"]),int(v["bytes"]))
                    for v in csv.DictReader(f) if v["event"]=="dma" and int(v["port"])==24
                    and 0x6961 <= (int(v["src"])&0x7fff) < 0x7161]
    raw = raw_transfers(d)
    assert raw == raw_transfers(base_dir) and raw
    return dict(**{k:r[k] for k in keys},client=sha(client/"sink165.sfc"),
                raw_payload_DMA_checked=len(raw), mean_dense_terms_ms=costs, dense_frames=dense)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("downloads","traces","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a = p.parse_args()
    results = dict(physical=physical(a.downloads),phases={})
    parent = PROBES/"nes-complete685/client01"
    raw = PROBES/"nes-output815/client"
    pins = read(ROOT/"analysis/prefix813-results.json")["builds"]["813"]
    for phase in (1,2):
        base = a.traces/f"nes-output809-mmc813-p{phase}"
        reference = read(base/"joint.json")
        assert reference["parameters"]["start"] == 7288416+(phase-1)*178684
        assert sha(base/"joint.json")==pins["phases"][str(phase)]["hashes"]["joint.json"]
        rows = {}
        for case,client_folder in (("mmc813",parent),("base",parent),("grant815",parent),("raw815",raw)):
            row = replay(a.traces,case,phase,reference,base,client_folder)
            image = (PROBES/"nes-output815/grant32/src/obj-nes-100/firmware.stm" if case=="grant815"
                     else PROBES/"nes-obj807/link807/src/obj-nes-100/firmware.stm" if case=="base"
                     else PROBES/"nes-prefix813/link813/src/obj-nes-100/firmware.stm")
            assert row["firmware"]==sha(image)
            rows[case] = row
            old = rows["mmc813"]
            assert all(old["dense_frames"][g]["work"]==row["dense_frames"][g]["work"] for g in old["dense_frames"])
            row["delta_dense_ms"]=row["dense_ms"]-old["dense_ms"]
            row["delta_ack_ms"]=ms(row["last_ACK"]-old["last_ACK"])
        selected = rows["raw815"]
        assert selected["delta_dense_ms"]<0 and selected["delta_ack_ms"]<0
        assert selected["restored951"] and selected["line951"]<=246 and selected["display959"]==2
        for g in (960,962):
            assert old["intervals"][g]==4 and selected["intervals"][g]==3
            assert selected["dense_frames"][g]["final_waits"]==0
        for row in rows.values():
            row["dense_frames"]={g:row["dense_frames"][g] for g in (958,959,960,962)}
        results["phases"][phase] = rows
    boot = read(a.traces/"nes-output815-boot01/result.json")
    stop = read(a.traces/"nes-output815-stop04/result.json")
    guard = read(PROBES/"nes-output815/guards.json")
    assert stop["client"] == sha(raw/"sink165.sfc") and stop["passed"] and len(stop["cases"])==11
    assert all(c["status"]==0xe4 and c["commits"]==c["generation"]-905 for c in stop["cases"])
    assert {(c["case"],c["generation"]) for c in stop["receipts"]}=={
        (case,g) for case in ("late_stop","cold","bad_manifest") for g in (906,907)}
    assert boot["passed"] and len(boot["cases"])==4 and all(c["passed"] for c in boot["cases"])
    assert guard["guards"]["ACK"]["corrupt_bits"]==152 and guard["guards"]["menu"]["rows"]["normal"]["released"]==1
    assert guard["object_recovery"]["service_stop_pending"]
    results["guards"]=dict(boot=boot,stop=stop,grant_firmware=guard["candidate"],
                           raw_ROM=read(raw/"build.json")["physical_ROM_B"],
                           raw_ROM_free=read(raw/"build.json")["physical_free_B"],
                           grant_guards={k:sha(PROBES/f"nes-output815/{k}.json") for k in ("guards","map","prefix")})
    a.output.write_text(json.dumps(results,indent=2)+"\n",encoding="utf8",newline="\n")
