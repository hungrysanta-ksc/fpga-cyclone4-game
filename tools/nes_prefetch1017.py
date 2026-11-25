"""Build a dot-zero late-demo clip around the measured OBJ set (ROM stays local)."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
import compare_nes_latency898 as clip
import geometry_nes_848 as geometry
from corpus_nes_848 import index
from replay_nes_mask820 import simulate
from prepare_nes_tile821 import prepare


FRAMES=list(range(3572,3601,4))


def build(action,temp,rom):
    work=temp/"nes-prefetch1017"
    board=temp/"nes-display1010-boardD"
    if action=="capture":
        from capture_nes_mask820 import capture
        capture(rom,temp/"nes-bonus698-mesen/Mesen.exe",work/"clip",FRAMES)
        return
    if action=="geometry":
        index(work/"clip",work/"split",work/"index.json",{"late":FRAMES})
        with patch.object(geometry,"ids",lambda:FRAMES):
            geometry.prepare(work/"split",work/"rtl")
        return
    if action=="rtl":
        def adapt(s):
            s=clip.once(s,"for(t=7*341+257;","for(t=0;")
            s=clip.once(s,"integer first,last,f,t,","integer sample_id,first,last,f,t,")
            return clip.once(s,"for(f=first;f<=last;f++)begin",
                             "for(sample_id=first;sample_id<=last;sample_id++)begin f=3572+4*sample_id;")
        simulate(board,work/"rtl",[(0,7)],adapt=adapt)
        ref=clip.PROBES/"nes-output823/link-826/src"
        prepare(work/"rtl",work/"split",rom,ref,work/"fixture",[("late",FRAMES)])
        clip.check_cache(temp,work/"fixture",work/"fixture",rom,held=True,
                         inputs=[(work/"fixture",work/"split",work/"rtl")],out=work/"hits")
        clip.check_sender(board,work/"fixture"/"late",ref,work/"sender-late")


def board_candidate(source, out):
    """Overlay on a private copy of the MMC1012 board sources."""
    from nes_raw506 import once,sha
    root=Path(__file__).resolve().parents[1]
    ref=json.loads((root/"analysis/trial1010-package.json").read_text())
    assert sha(source/"output_files/board.sof")==ref["image"]["SOF"]
    out.mkdir(parents=True, exist_ok=True)
    ports="input wire guide_record, input wire [12:0] guide_tag, input wire [7:0] guide_mask,"
    forward=".guide_record(guide_record),.guide_tag(guide_tag),.guide_mask(guide_mask),"
    def edit(file, pairs):
        text=(source/file).read_text()
        for old,new in pairs:
            text=once(text,old,new)
        (out/file).write_text(text,newline="\n")
    edit("nes_live_joint.sv",[("nes_direct206 direct_path(", """reg object_query1017;
 always @(posedge clk) object_query1017<=native_frame_query && native_frame_query_kind==2;
 nes_direct206 direct_path(.guide_record(object_query1017&&native_frame_response&&native_frame_hit),
 .guide_tag(native_frame_data[12:0]),.guide_mask(native_frame_data[45:38]),""")])
    edit("nes_direct206.sv",[("input wire cap_start",ports+" input wire cap_start"),("source(.page963","source("+forward+".page963")])
    edit("nes_source_tile192.sv",[("input wire cap_start",ports+" input wire cap_start"),("ahead(.page963","ahead("+forward+".page963")])
    reader=(Path(__file__).parent/"nes_guide1017.svh").read_text()
    edit("nes_e9_rows914.sv",[
        ("input wire page963",ports+" input wire page963"),
        (" assign request=foreground||spec||aux952;",reader+"\n assign request=foreground||spec||aux952||guide_request;"),
        ("physical_address=aux952?","physical_address=guide_request?guide_address:aux952?"),
        ("cache_index(ahead952);","cache_index(guide_probe?guide_address:ahead952);"),
        ("if(lookup_demand||lookup_hint||probe952)","if(lookup_demand||lookup_hint||probe952||guide_probe)"),
        ("else if(lookup_hint||probe952)lookup<=rows[cache_index(ahead952)];",
         "else if(lookup_hint||probe952||guide_probe)lookup<=rows[cache_index(guide_probe?guide_address:ahead952)];"),
        ("spec_owner<=spec||aux952;","spec_owner<=spec||aux952||guide_request;"),
        ("if(take&&!spec&&candidate)","if(take&&!spec&&!guide_request&&candidate)")])
def stimulus(temp,rom,downloads):
    import hashlib
    from analyze_nes_scroll229 import records,FETCH
    from read_nes_supply1016 import decode as detail, NES_MS
    from read_nes_tail1012 import decode as tail, MS, ARM_TICK
    from test_nes_service509_schedule import Calendar
    root=Path(__file__).resolve().parents[1]
    work=temp/"nes-prefetch1017"
    bench=work/"test"
    bench.mkdir(exist_ok=True)
    clk=21477.272
    def write(name,values):
        (bench/name).write_text("".join(f"{v:x}\n" for v in values))
    raw=rom.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=json.loads((work/"clip/capture.json").read_text())["rom"]:
        raise ValueError("capture ROM differs")
    chrdata=raw[16+512*bool(raw[6]&4)+16384*raw[4]:]
    assert len(chrdata)==131072
    write("chr.hex",chrdata)
    def objects(frame):
        words={}
        for line in (work/f"rtl/frame{frame}.query").read_text().splitlines():
            kind,index,value=line.split()
            if kind=="2":
                assert words.setdefault(int(index),int(value,16))==int(value,16)
        assert sorted(words)==list(range(len(words)))
        return [(w&8191,(w>>38)&255) for w in words.values()]
    obj=objects(3600)
    write("objects.hex",[tag<<8|mask for tag,mask in obj])
    earliest={}
    for row in records(work/"split/3600/ppu-fetch.bin",FETCH):
        _,y,d,_,value,physical,*_=row
        if 7<=y<232 and 257<=d<=320 and d%8 in (5,7):
            assert chrdata[physical]==value
            earliest.setdefault(physical,(y,d))
    cal=Calendar(temp/"nes-service509-rom03")
    windows=[]
    for a,b in cal.pairs:
        if not windows or a-windows[-1][-1]>40000:windows.append([])
        windows[-1].append(a)
    orig=json.loads((root/"analysis/supply1015-results.json").read_text())["runs"][:2]
    pins=json.loads((root/"analysis/supply1016-hardware.json").read_text())["runs"]
    report=[]
    for idx,(r,pin) in enumerate(zip(orig,pins),1):
        f,=downloads.glob(f"nes-frame-mmc1016-{idx}*.bin")
        assert hashlib.sha256(f.read_bytes()).hexdigest()==pin["hashes"]["frame"]
        d=detail(f.read_bytes())["detail"]
        ops=[op for tile in d["tiles"] for op in tile["reads"]]
        shape=[(op["tag"]*16+op["plane"]*8+op["row"],op["source"]) for op in ops]
        if idx==1:
            first_shape=shape
            write("reads.hex",[0x200000+a for a,src in shape])
            write("warm.hex",[int(src=="row_cache") for a,src in shape])
        assert shape==first_shape and len(shape)==112
        assert all(earliest[a][0]<242 for a,src in shape if src=="demand_ROM")
        fb,=downloads.glob(f"nes-frame-mmc1012-{idx}*.bin")
        assert hashlib.sha256(fb.read_bytes()).hexdigest()==r["log_sha256"]
        entry,=[x for x in tail(fb.read_bytes(),1012)["rows"] if x["generation"]==r["generation"]]
        ticks=r["FPGA_event_ticks"]
        mins,maxs=r["measured_final_ACK_to_ARM_E0_ms"]
        age=entry["input_to_E0_ms"]-(ticks["final_ACK"]-ticks["first_E9"])*MS
        bounds=[age-maxs-MS-2*ARM_TICK,age-mins+MS+2*ARM_TICK]
        # Preserve the observed first bank return for the third chunk. Use the
        # upper quantization edge rather than giving the candidate an early bank.
        (bench/f"return{idx}.txt").write_text(str(round((1+d["chunks"][0]["return_host_tick"])*65536/84000*clk)))
        w=windows[idx-1]+windows[idx]
        center=lambda x: x-w[0]+320000
        e9=center(windows[idx][0])-11*16384
        source=e9-int(clk*bounds[0])
        assert source>2000 and source+len(obj)*2<center(w[0])
        (bench/f"phase{idx}.txt").write_text(" ".join(map(str,[len(w),len(obj),source,e9,*map(center,w)])))
        if idx==1:
            # Same source, bank return and physical grant calendar. Shift only
            # the client by the half-frame offset of replay_nes_tile821.main().
            shift=178684
            (bench/"phase3.txt").write_text(" ".join(map(str,[len(w),len(obj),source+shift,e9+shift,*map(center,w)])))
            (bench/"return3.txt").write_bytes((bench/"return1.txt").read_bytes())
        # Prior VBlank line 246 versus the observed show (at or after line 225).
        # Maximally optimistic: remove the WHOLE E9-to-publish interval.
        min_lead=(262-(246-225+1))*1364/clk
        least_needed=min_lead-(ticks["show"]-ticks["SEAL"]+1)*MS
        max_tile=(ticks["last_tile_publish"]-ticks["first_E9"]+1)*MS
        report.append(dict(run=idx,generation=r["generation"],input_complete_before_E9_ms=bounds,
             conservative_geometry_to_window_ms=(center(w[0])-source)/clk,
             replay_prior_grants=len(windows[idx-1]),bank_return_host_ticks=[c["return_host_tick"] for c in d["chunks"]],
             minimum_SEAL_advance_for_prior_VBlank_ms=least_needed,maximum_tile_interval_ms=max_tile,
             missing_even_if_tile_instant_ms=least_needed-max_tile))
    assert all(any(tag==a//16 and (mask>>(a%8))&1 for tag,mask in obj)
               for a,src in shape if src=="demand_ROM")
    proof=dict(source_frame=3600,source_hash=hashlib.sha256(raw).hexdigest(),
        object_records=len(obj),previous_frame_row0={f:any(t==6270 and m&1 for t,m in objects(f)) for f in (3588,3592,3596)},
        first_native_address_row0=earliest[6270*16],last_native_pair_for_two_tags=max(earliest[t*16+b] for t in (6270,6271) for b in range(16)),
        calendar=cal.summary, trials=report)
    (bench/"source.json").write_text(json.dumps(proof,indent=2)+"\n")
def summarize(temp,output):
    import hashlib
    import re
    bench=temp/"nes-prefetch1017/test"
    evidence=json.loads((bench/"source.json").read_text())
    rate=21477.272
    def fields(path, prefix):
        lines=path.read_text(errors="replace").splitlines()
        (line,)=[s for s in lines if s.startswith("# "+prefix+" ")]
        assert not any("** Fatal:" in s for s in lines)
        return {key:int(value) for key,value in re.findall(r"(\w+)=(\d+)",line)}
    results=[]
    for phase in (1,2,3):
        ref=fields(bench/f"original-{phase}.log","SOURCE")
        modes=[]
        for mode in (0,1,2):
            path=bench/f"phase-{phase}-mode-{mode}.log"
            assert "PASS checked all rows, preserved hits, STOP drained" in path.read_text(errors="replace")
            rows=fields(path,"RESULT")
            tile=fields(bench/f"source-{phase}-{mode}.log","SOURCE")
            assert tile["bytes"]==464
            if mode==0:assert tile==ref
            modes.append(dict(mode=mode,rows=rows,tile=tile,
                first_row_wait_ms=round(rows["first_wait"]/rate,6),
                last_tile_ms=round(tile["last"]/rate,6),
                last_tile_gain_ms=round((ref["last"]-tile["last"])/rate,6)))
        results.append(modes)
    evidence.update(nominal_NES_clocks_per_ms=rate,replay=results,
        baseline_firmware_sha256=json.loads((Path(__file__).resolve().parents[1]/"analysis/trial1012-package.json").read_text())["firmware"],
        phases=["replay aligned to measured wait, run 1","replay aligned to measured wait, run 2",
                "phase 1, same grant times and bank return age, client delayed 178684 clocks"],
        modes=["MMC1012 control","other valid entries occupy only the 96 observed hits",
               "collision at each of the 16 other indices; original valid rows protected"],
        constraints=dict(nominal_first_grant_anchor_NES_ticks=11,
            early_data="Available input-complete lower bound and committed native OBJ records, not a simultaneous capture of the physical exporter and arbiter",
            bank_return="first bank latest quantization edge; the third bank group waits for it",
            transfer="same ordered 112 row-pair operands; short OBJ reconstruction checked against local CHR bytes",
            display="necessary bound from hardware SEAL and show stamps, conditional on unchanged post-tile schedule; no candidate physical reveal timestamp",
            initial_cache="96 row keys known, nonmatching valid bits not observable from the field log",
            source_history="8 source frames reproduced; final planner's mapdirty=0, unlike the field capture's 23; its publication is not a matched reference"),
        inputs={file:hashlib.sha256((temp/"nes-display1010-boardD"/file).read_bytes()).hexdigest()
                for file in ("nes_live_joint.sv","nes_direct206.sv","nes_source_tile192.sv","nes_e9_rows914.sv","nes_tile205.sv","sink-program.hex")})
    output.write_text(json.dumps(evidence,indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("capture","geometry","rtl","board","stimulus","report"))
    p.add_argument("temp",type=Path);p.add_argument("rom",type=Path)
    a=p.parse_args()
    if a.action=="board": board_candidate(a.temp/"nes-display1010-boardD",a.temp/"nes-prefetch1017"/"board")
    elif a.action=="report": summarize(a.temp,Path(__file__).resolve().parents[1]/"analysis/prefetch1017-results.json")
    elif a.action=="stimulus": stimulus(a.temp,a.rom,Path.home()/"Downloads")
    else: build(a.action,a.temp,a.rom)
