"""Replay the observed render-off interval at the collector's release boundary, bracketing it with real stimuli."""
import json
from pathlib import Path
import shutil
import sys

from analyze_nes_scroll229 import WRITE, records
from build_nes_game164 import RGB
from nes_raw506 import once
from replay_nes_mask820 import simulate


def check(board, rtl, split, out):
    out.mkdir(parents=True, exist_ok=False)
    for f in (1544,1557):
        for ext in ("hex","palette"):
            shutil.copyfile(rtl/f"frame{f}.{ext}",out/f"frame{f}.{ext}")
    masks=[]
    for f in range(1545,1557):
        d=split/str(f)
        assert all((d/n).stat().st_size==0 for n in ("ppu-fetch.bin","nametable.bin","rows.bin"))
        rgb=(d/f"frame-{f:04d}.rgb").read_bytes()
        assert rgb==bytes(256*240*3)
        masks.extend(v for k,_,_,_,a,v in records(d/"writes.bin",WRITE) if k==0 and a==0x2001)
    assert masks and set(masks)=={0}
    black=next(i for i,c in enumerate(RGB) if bytes.fromhex(c)==bytes(3))
    def blank(s):
        s=once(s,"reg enable=0;", "reg allow_discard=1; integer releases=0; always @(posedge clk) if(exporter_release) releases++; reg enable=0;")
        s=once(s,".discard_permitted(1'b1)",".discard_permitted(allow_discard)")
        s=once(s,'name=$sformatf("frame%0d.hex",f);','if(f==1544 || f==1557) begin name=$sformatf("frame%0d.hex",f);')
        s=once(s,"palette=palfile[0];","palette=palfile[0]; end")
        s=once(s,"drive=stimulus[t];",f"if(f==1544 || f==1557)drive=stimulus[t]; else drive={{1'b0,6'd{black},100'b0}};")
        return once(s,"   if(!owned||!geometry_valid)",'''   if(f>1544 && f<1557)begin
    if(!owned || geometry_valid)$fatal(1,"blank validity %d",f);
    allow_discard=0;records=0;rc=releases;enable=1'b1;
    repeat(8)@(negedge clk);
    if(!owned || releases!=rc || records!=0)$fatal(1,"prior display %d",f);
    allow_discard=1;repeat(32)@(negedge clk);
    if(owned || releases!=rc+1 || records!=0 || export_error!=2)$fatal(1,"blank release %d",f);
    enable=0;frames++;$display("BLANK848 %0d no records one release",f);continue;
   end
   if(!owned||!geometry_valid)''')
    simulate(board,out,[(1544,1557)],adapt=blank)
    report=(out/"1544.log").read_text()
    assert all(report.count(f"BLANK848 {f} no records one release")==1 for f in range(1545,1557))
    result=dict(blank_ids=list(range(1545,1557)), mask_writes=masks, release_hold_clocks=8,
                exported_records=[len((out/f"frame{f}.wire").read_text().splitlines()) for f in (1544,1557)])
    (out/"blank.json").write_text(json.dumps(result))


if __name__=="__main__":
    check(*[Path(p).resolve() for p in sys.argv[1:]])
