"""Exercise physical loader, checked source/cache, staging, chunk aperture and STOP."""
import argparse,binascii,json,shutil,struct,subprocess
from test_nes_raw506_joint import wire_plan
from pathlib import Path
from check_nes_fault641 import digest,evidence
from nes_raw506 import once

def testbench(decoded=False):
    src=Path(__file__).with_name("nes_bg659_tb.sv").read_text()
    prefix=src[:src.index(" reg [23:0] address=")].replace("module bg659_tb","module word660_tb")
    boot=src[src.index(" nes_rom_boot boot"):src.index(" reg [23:0] boot_bus")]
    boot=once(boot,"issue || (core && !owned)","request").replace("issue?request_address:core_address","request_addr").replace(".window_word(word_data)",".bg_word(word_data)")
    checks=src[src.index(" task check("):src.index(" task core_read(")]
    load=src[src.index(' initial begin\n  $readmemh("game.hex"'):src.index('  fd=$fopen("tiles.txt"')]
    staging=Path(__file__).with_name("nes_word660_staging.sv").read_text(encoding="utf-8-sig")
    tb=prefix+staging+boot+checks+""" integer i,j,fd,gen,k,s,t,have=0;reg[47:0] rowdata;reg[103:0] alts;reg[7:0] m,am;
"""+load+""" fd=$fopen("plans.txt","r");
  while($fscanf(fd,"%d %d %d %d %h %h %h %h",gen,k,s,t,rowdata,m,am,alts)==8)begin
   if(have && gen!=g)begin
    @(negedge clk);ending=1;wait(end_ready);@(posedge clk);@(negedge clk);ending=0;
    wait(end_sealed);wait(!chunk);repeat(16)@(negedge clk);
   end
   @(negedge clk);g=gen;kind=k;slot=s;tag=t;rows=rowdata;mask=m;altmask=am;alt=alts;
   valid=1;wait(accepted);@(posedge clk);@(negedge clk);valid=0;wait(done);have=1;
  end
  @(negedge clk);ending=1;wait(end_ready);@(posedge clk);@(negedge clk);ending=0;
  wait(end_sealed);wait(!chunk);repeat(16)@(negedge clk);
  if(last_token==0)$fatal(1,"no chunks");
  // Cancel a partial staged BG and drain the physical reply before reuse.
  g=1100;kind=0;slot=100;tag=8000;rows=48'o7766554433221100;mask=255;altmask=0;
  valid=1;wait(accepted);@(posedge clk);@(negedge clk);valid=0;
  wait(tv&&idx==2);wait(source.arb_request && source.arb_ready);@(posedge clk);@(negedge clk);
  cancel=1;#1;if(tv||chunk)$fatal(1,"STOP published partial tile");
  repeat(24)@(negedge clk);if(tv||chunk||done)$fatal(1,"late publish");cancel=0;
  repeat(20)@(negedge clk);if(!drained)$fatal(1,"undrained");
  $display("PASS660 physical loader, native CHECK, source word reads, bulk chunks, STOP drain");$finish;
 end
 initial begin #380000000;$fatal(1,"timeout g=%d k=%d s=%d ready=%b busy=%b permit=%b valid=%b end=%b chunk=%b",g,kind,slot,plan_ready,source.busy,permit,valid,end_sealed,chunk);end
endmodule
"""

    if not decoded:return tb
    extra=Path(__file__).with_name("nes_word660_decoder.sv").read_text()
    tb=once(tb," reg host=0;always #5.952"," always #5.952");extra=" reg host=0;\n"+extra
    tb=once(tb," nes_source_tile192 #",extra+"\n nes_source_tile192 #")
    tb=once(tb,".plan_kind(kind),.plan_generation(g),.plan_slot(slot),.plan_tag(tag),.plan_rows(rows)",
        ".plan_short(p_short),.plan_kind(p_kind),.plan_generation(p_generation),.plan_slot(p_slot),.plan_tag(p_tag),.plan_rows(p_rows)")
    tb=once(tb,".plan_mask(mask),.plan_alt_mask(altmask),.plan_alt_tags(alt)",".plan_mask(p_mask),.plan_alt_mask(p_am),.plan_alt_tags(p_alt)")
    tb=once(tb,".plan_valid(valid&&permit)",".plan_valid(valid&&permit&&p_valid)")
    tb=once(tb,'"%d %d %d %d %h %h %h %h",gen,k,s,t,rowdata,m,am,alts)==8','"%d %d %d %d %h %h %h %h %d %h %h",gen,k,s,t,rowdata,m,am,alts,plen,packet,pcrc)==11')
    tb=once(tb,"   valid=1;wait(accepted);","   publish();valid=1;wait(accepted);")
    return once(tb,"  valid=1;wait(accepted);@(posedge clk);@(negedge clk);valid=0;\n  wait(tv&&idx==2);",
        "  packet=56'h1f400064044c80;plen=7;pcrc=packet_crc();publish();valid=1;wait(accepted);@(posedge clk);@(negedge clk);valid=0;\n  wait(tv&&idx==2);")


def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    files=[s+".sv" for s in ("nes_rom_loader","nes_rom_physical","nes_rom_boot","nes_source_tile192","nes_tile205",
        "nes_native_arbiter165","nes_chr_cache611","nes_obj_capture611","nes_tile_bulk206","nes_domain_reset124","nes_native_mailbox206","nes_bulk_aperture188")]
    if a.decoded:files.append("nes_plan_batch206.sv")
    for f in files:shutil.copyfile(a.board/f,a.out/f)
    (a.out/"tb.sv").write_text(testbench(a.decoded),newline="\n")
    assert digest(a.game)==evidence("mmc480-verification.json")["live_functional"]["rom_sha256"]
    raw=a.game.read_bytes()[16:];(a.out/"game.hex").write_text(raw.hex("\n")+"\n")
    # The ARM can reorder OBJ plans. Feed the board the issued order, not
    # the original planner enumeration. Match each plan by slot and kind.
    ordered={}
    for line in (a.reference/"packets.jsonl").read_text().splitlines():
        _,_,packet,payload=json.loads(line);p=bytes.fromhex(packet)
        if p[0]!=7:continue
        gen=int.from_bytes(p[8:10],"little");size=32 if p[1] else 16
        first=int.from_bytes(p[10:12],"little")//size
        ordered.setdefault(gen,[]).extend((p[1],first+i) for i in range(len(bytes.fromhex(payload))//size))
    with (a.out/"plans.txt").open("w") as f:
        for gen in range(905,958):
            plans={}
            for _,h in json.loads((a.plans/f"frame{gen}/plans.json").read_bytes()):
                p=bytes.fromhex(h);key=(int(p[6]==1),int.from_bytes(p[2:4],"little"))
                assert key not in plans;plans[key]=h
            assert set(ordered.get(gen,[]))==set(plans) and len(ordered.get(gen,[]))==len(plans)
            for key in ordered.get(gen,[]):
                h=plans[key]
                p=bytes.fromhex(h);g,s,t,k,m=struct.unpack_from("<HHHBB",p);assert g==gen
                rows=sum(v<<(3*i) for i,v in enumerate(p[8:24]))
                alt=struct.unpack_from("<8H",p,24);mask=sum(1<<i for i,v in enumerate(alt) if v!=65535)
                tags=sum(v<<(13*i) for i,v in enumerate(alt) if v!=65535)
                extra=[]
                if a.decoded:
                    body=wire_plan(p)
                    extra=[len(body),f"{int.from_bytes(body,'little'):x}",f"{binascii.crc_hqx(body,65535):x}"]
                print(g,k,s,t,f"{rows:x} {m:x} {mask:x} {tags:x}",*extra,file=f)
    for tool,args in (("vlib",["work"]),("vlog",["-sv",*files,"tb.sv"]),("vsim",["-c","-quiet","word660_tb","-do","onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0"])):
        with (a.out/(tool+".log")).open("wb") as log:
            subprocess.run([a.bin/(tool+".exe"),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=750,check=True)
    assert "PASS660" in (a.out/"vsim.log").read_text()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("board","out","bin","plans","game","reference"):p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--decoded",action="store_true");run(p.parse_args())
