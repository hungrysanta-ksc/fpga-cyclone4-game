"""Actual collector/export COMMIT, capture pins and lease retirement on 53 PPU traces.
The retire pulse stands for the separately verified final ACK/EA path; not a CPU timing run.
"""
import argparse,json,shutil,subprocess
from pathlib import Path
from check_nes_wire600 import ROOT,pin,read,sha
from nes_raw506 import once

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    pin(a.samples,read(ROOT/'analysis/snoop601-verification.json')['fixture_sha256'])
    values={};queries={};g=904
    for l in a.samples.read_text().splitlines():
        op,k,x,v,h=l.split();x=int(x,16);v=int(v,16)
        if op=='0':g+=1;queries[g]=[]
        elif op=='1':
            assert x not in values or values[x]==v
            values[x]=v
        elif op=='2' and k=='1':queries[g].append((x,v,int(h)))
    (a.out/'bytes.hex').write_text(''.join(f'{values.get(i,0):02x}\n' for i in range(131072)))
    meta=read(a.geometry/'result.json');pin(a.geometry/'result.json',read(ROOT/'analysis/geometry230-verification.json')['stimulus_result_sha256'])
    for g in (range(951,953) if getattr(a,'overlap',False) else range(905,958)):
        f=next(r for r in meta['frames'] if r['frame']==g)
        pin(a.geometry/f'frame{g}.hex',f['stimulus_sha256'])
        for ext in ('hex','palette'):shutil.copy(a.geometry/f'frame{g}.{ext}',a.out)
        (a.out/f'frame{g}.queries').write_text(''.join(f'{x:x} {v:x} {h}\n' for x,v,h in queries[g]))
    s=(ROOT/'tests/nes-functional/geometry230_tb.sv').read_text().replace('geometry230_tb','lifecycle611_tb')
    s=once(s,'nes_native_frame201 frame(.*);','''wire effective_release,lease_valid,retire_permitted,export_permitted,waiting_display,lease_fault;
 reg retire_commit=0;reg [15:0] retire_generation=0;
 wire [31:0] captured_epoch;wire [15:0] captured_generation;
 nes_native_capture201 frame(.source_ready(1'b1),.source_is_rom(1'b1),.source_writing(1'b0),.live_epoch(32'd7),
  .reader_drained(1'b1),.*);
 @CACHE@
''')
    live=(a.board/'nes_live_joint.sv').read_text()
    start=live.index(' .cap_start(',live.index('nes_direct206 direct_path('));end=live.index('.nes_clk(clk)',start)
    ports=live[start:end]
    for old,new in [('cap_start','start'),('cap_generation','capture_gen'),('cap_seal','seal'),('cap_sample','sample'),('cap_address','sample_address'),('cap_data','sample_data'),
                    ('capture_begin611','capture_begin'),('native_generation','generation'),('native_frame_owned','owned'),('native_geometry_valid','geometry_valid'),
                    ('native_active','active'),('tap_ce','ppu_ce'),('native_obj_valid','obj_valid'),('native_obj_low','obj_low'),('native_obj_high','obj_high'),
                    ('ppumem_read','ppu_read'),('rom_ppu_valid','ppu_valid'),('ppumem_addr','physical_address'),('ppumem_din','rombytes[physical_address[16:0]]')]:ports=ports.replace(old,new)
    cache='''reg [7:0] rombytes[0:131071];
 reg cq=0;reg [15:0] cgen;reg [16:0] ca;wire cr,ch,cs,ss,qr;wire [7:0] cd;
 nes_obj_capture611 cache(.clk(clk),.reset(reset),.stop(rom_fault),.immutable(1'b1),
 @PORTS@
 .release_bank(retire_commit&&retire_permitted),.release_gen(retire_generation),
 .query(cq),.query_gen(cgen),.query_address(ca),.query_ready(qr),.response(cr),.hit(ch),.data(cd),.start_ready(cs),.sample_ready(ss));
 integer queryfile,qaddr,qval,qhit,oldaddr=0,oldval=0,oldgen=0,totalqueries=0,totalhits=0,retired=0;
 reg previous_hit=0;
 task ask(input integer gen,addr,val,expected);begin
  @(negedge clk);cgen=gen;ca=addr;cq=1;
  if(!qr)$fatal(1,"query port");
  @(negedge clk);cq=0;
  if(!cr||ch!==expected[0]||(expected&&cd!==val[7:0]))$fatal(1,"capture data gen=%d addr=%h expected=%d actual=%b",gen,addr,expected,ch);
 end endtask
 task retire_previous;begin
  if(previous_hit)ask(oldgen,oldaddr,oldval,1);
  if(!lease_valid||captured_generation!=oldgen)$fatal(1,"lease owner");
  retire_generation=oldgen;retire_commit=1;@(negedge clk);retire_commit=0;
  if(lease_valid||lease_fault||!active)$fatal(1,"EA released next capture");
  if(previous_hit)ask(oldgen,oldaddr,oldval,0);
  retired++;
 end endtask
 always @(posedge clk) if(!reset)begin
  if(capture_begin&&!cs)$fatal(1,"uncleared bank at real START");
  if(cache.sample&&!ss)$fatal(1,"sample port overrun");
 end
'''.replace('@PORTS@',ports)
    s=s.replace('@CACHE@',cache)
    s=s.replace('if(!$value$plusargs("LAST=%d",last))last=975;','if(!$value$plusargs("LAST=%d",last))last=957;\n  $readmemh("bytes.hex",rombytes);')
    s=s.replace('@(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);','''@(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
    if(t==8*341 && f>first)retire_previous;''')
    s=s.replace('name=$sformatf("frame%0d.cfg",f);', '''name=$sformatf("frame%0d.queries",f);queryfile=$fopen(name,"r");previous_hit=0;
   while(!$feof(queryfile))begin
    rc=$fscanf(queryfile,"%h %h %d\\n",qaddr,qval,qhit);
    if(rc==3)begin
     ask(generation,qaddr,qval,qhit);totalqueries++;totalhits+=qhit;
     if(qhit)begin oldaddr=qaddr;oldval=qval;previous_hit=1;end
    end
   end
   $fclose(queryfile);oldgen=generation;
   name=$sformatf("frame%0d.cfg",f);''')
    s=s.replace('if(export_error)$fatal', 'if(!lease_valid||captured_generation!=generation||lease_fault)$fatal(1,"export COMMIT lease");\n   if(previous_hit)ask(oldgen,oldaddr,oldval,1);\n   if(export_error)$fatal')
    s=s.replace('$display("PASS GEOMETRY230 frames=%0d",frames);', '$display("PASS611 lifecycle frames=%0d queries=%0d hits=%0d retired=%0d",frames,totalqueries,totalhits,retired);')
    if getattr(a,'overlap',False):
        assert '.start_permitted(export_permitted204||reader_drained204)' in live
        assert '.ack_accept(native_ack_data[16]&&export_permitted204)' in live
        s=once(s,'first=905;', 'first=951;')
        s=once(s,'last=957;', 'last=952;')
        s=once(s,'.enable(enable),','.start_permitted(1\'b1),.enable(enable&&(export_permitted||lease_valid)),')
        s=once(s,'.ack_accept(ack_accept),','.ack_accept(ack_accept&&export_permitted),')
        s=once(s,'reg previous_hit=0;', 'integer keepaddr,keepval,keepgen;reg previous_hit=0;')
        s=once(s,'if(t==8*341 && f>first)retire_previous;',
               'if(t==8*341 && f>first)begin if(!previous_hit || !active)$fatal(1,"no active 952 capture or 951 hit"); ask(oldgen,oldaddr,oldval,1);keepaddr=oldaddr;keepval=oldval;keepgen=oldgen;end')
        s=once(s,'wait(done);wait(!busy);','''if(f==952)begin
    wait(tx_valid&&tx_data[95:93]==7&&tx_data[76:64]==1);@(posedge clk);@(negedge clk);if(!lease_valid||export_permitted||captured_generation!=keepgen||records<7)$fatal(1,"overlap");
    ask(keepgen,keepaddr,keepval,1);
    retire_generation=keepgen;retire_commit=1;@(negedge clk);retire_commit=0;
    if(!owned||!geometry_valid||lease_valid||lease_fault||!export_permitted)$fatal(1,"EA affected 952");
    ask(keepgen,keepaddr,keepval,0);ack_generation=generation;ack_valid=1;
    @(negedge clk);ack_valid=0;retired++;
   end
   wait(done);wait(!busy);''')
        s=once(s,'begin ack_valid<=1;ack_generation<=generation;end',
               'begin ack_valid<=(f!=952);ack_generation<=generation;end')
    (a.out/'test.sv').write_text(s,newline='\n')
    names=['nes_native_capture201','nes_capture_lease201','nes_native_frame201','nes_native_planes165','nes_patch_capture181','nes_patch_rows181','nes_native_compact181','nes_native_raster181','nes_native_export203','nes_obj_capture611']
    for n in names:shutil.copy(a.board/(n+'.sv'),a.out)
    for tool,args in [('vlib',['work']),('vlog',['-sv',*[n+'.sv' for n in names],'test.sv']),('vsim',['-c','lifecycle611_tb','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0'])]:
        with (a.out/(tool+'.log')).open('wb') as log:
            subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
    text=(a.out/'vsim.log').read_text();marker=('PASS611 lifecycle frames=2 ' if getattr(a,'overlap',False) else 'PASS611 lifecycle frames=53 queries=1328 hits=1200 retired=52')
    assert marker in text
    if getattr(a,'overlap',False):assert 'retired=1' in next(line for line in text.splitlines() if marker in line)
    (a.out/'result.json').write_text(json.dumps(dict(scope=__doc__ if not getattr(a,'overlap',False) else next(line for line in text.splitlines() if marker in line),inputs={n:sha(a.board/(n+'.sv')) for n in names},top=sha(a.board/'nes_live_joint.sv'),bench=sha(a.out/'test.sv'),log=sha(a.out/'vsim.log'),samples=sha(a.samples),geometry=sha(a.geometry/'result.json')),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('board','out','bin','samples','geometry'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--overlap',action='store_true',help='Exercise 951 OBJ reads during capture and export of 952, before old EA')
    run(p.parse_args())
