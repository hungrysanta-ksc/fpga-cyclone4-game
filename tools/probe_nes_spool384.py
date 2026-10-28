# SPDX-License-Identifier: MIT
"""383 WRAM-first consumer service on actual377ARM/375RTL shared schedule.

Native source-job boundaries/data must match exactly;unknown profiles fail.
Recorded native PPU service is charged after checked source storage and seal.
Cold prefix is unchanged;native prior-bank images are explicit fixtures.
"""
import csv,json,shutil
from pathlib import Path
import probe_nes_commit382 as previous
from nes_delta231 import ROOT,BASE,sha,once
NATIVE=BASE/'probes/nes-spool383/native07'
engine=previous.engine;old_prepare=engine.prepare

EXTRA=r'''
 reg [63:0] records384[0:255],tail384[0:8191];reg [7:0] expected384[0:16383];
 integer record384=0,stored384=0,byte384=0,offset384=0,recordlen384=0,preflight384=0,budget384=0,tailcount384=0;
 integer overhead384[0:4];reg [63:0] config384[0:8];
 task reset384;
 begin
  if(f>=907)begin
   $readmemh($sformatf("spool-records%0d.hex",f),records384);$readmemh($sformatf("spool-data%0d.hex",f),expected384);
   $readmemh($sformatf("spool-tail%0d.hex",f),tail384);$readmemh($sformatf("spool-config%0d.hex",f),config384);
   record384=0;stored384=0;offset384=0;byte384=0;recordlen384=0;
   preflight384=config384[0];budget384=config384[1];tailcount384=config384[2];
   for(integer j=0;j<5;j++)overhead384[j]=config384[3+j];
  end
 end endtask
 task store_begin384(input integer kind384,pos384,n384);
  reg [63:0] r384;
 begin
  if(f>=907)begin
   if(recordlen384||record384>=records384[0])$fatal(1,"spool record capacity384");
   r384=records384[record384+1];
   if(r384[7:0]!=kind384||r384[23:8]!=pos384||r384[39:24]!=n384)
    $fatal(1,"native source profile mismatch384 f%0d record%0d got%0d/%0d/%0d expected%h",f,record384,kind384,pos384,n384,r384);
   recordlen384=n384;byte384=0;
  end
 end endtask
 task store_byte384(input [7:0] b384);
 begin
  if(f>=907)begin
   if(byte384>=recordlen384||b384!==expected384[offset384+byte384])$fatal(1,"native staged byte mismatch384");
   byte384++;
  end
 end endtask
 task store_end384;
 begin
  if(f>=907)begin
   if(byte384!=recordlen384||!recordlen384)$fatal(1,"incomplete WRAM store384");
   $fwrite(events261,"stored384,%0d,%0d,%0d,%0t\n",f,record384,recordlen384,$time);
   offset384+=recordlen384;recordlen384=0;record384++;stored384++;
  end
 end endtask
 task display_spool384;
  integer n384,window384,scroll384;reg [63:0] e384;reg [23:0] a384;reg [7:0] b384;reg [31:0] tok384;realtime base384;
 begin
  if(recordlen384||stored384!=records384[0])$fatal(1,"PPU before full WRAM storage384");
  tok384=dut.flow.last_map_token;scroll384=0;
  // Native post-view record construction/budget/control is real CPU time.
  #(preflight384*MASTER_NS378);
  while(!blank378()||357368-phase378()<budget384)begin
   #(92*MASTER_NS378);if(source_fault||flow_fault||test_abort)return;
  end
  base384=$realtime;window384=(romcycle267+SNES_PHASE378)/357368;
  $fwrite(events261,"vblank384,%0d,%0t,%0d,%0d\n",f,$time,phase378(),window384);
  for(integer i384=1;i384<=tailcount384;i384++)begin
   e384=tail384[i384];until378(base384+e384[63:40]*MASTER_NS378);a384=e384[31:8];b384=e384[7:0];
   if(source_fault||flow_fault||test_abort)return;
   if(!blank378())$fatal(1,"native PPU/commit left VBlank384");
   if(a384>=24'h006000)begin
    if(a384>=24'h006048&&a384<=24'h00604f)b384=tok384[a384[1:0]*8+:8];
    if(e384[32])wr261(a384,b384);
    else begin
     rd261(a384,b384);
     if(a384==24'h006001)begin if(b384[7:6])return;end
     else if(b384!==tok384[a384[1:0]*8+:8])$fatal(1,"native final token384");
    end
   end else if(e384[32])begin
    if(a384==24'h00210d||a384==24'h00210e)begin
     if(scroll384>=4||b384!==view378(8+scroll384))$fatal(1,"native scroll/view mismatch384");scroll384++;
    end
    ppu378[a384]=b384;
    $fwrite(events261,"ppu384,%0d,%0d,%0d,%0t,%0d\n",f,a384,b384,$time,phase378());
   end
  end
  if(scroll384!=4||ppu378[16'h2100]!=15||ppu378[16'h2107]!=(~display_serial373[0]?8'h51:8'h31))$fatal(1,"native final PPU bank384");
  $fwrite(events261,"present384,%0d,%0t,%0d,%0d\n",f,$time,window384,phase378());wait(!v_sealed);
 end endtask
'''


def profile(d,f):
 q=NATIVE/str(f);jobs=json.loads((q/'fixture.json').read_text());ev=[list(map(int,x)) for x in csv.reader((q/'events.csv').read_text().splitlines())]
 tm=list(csv.DictReader((q/'timings.csv').read_text().splitlines()));first_ppu=next(int(x['clock']) for x in tm if x['phase']=='PPU_trigger')
 first_poll=next(x[4] for x in ev if x[1:3]==[0,0x4212]);last_view=max(x[4] for x in ev if x[1]==0 and 0x6070<=x[2]<=0x607b)
 origin=max(x[4] for x in ev if x[1:3]==[0,0x4212] and x[4]<first_ppu)
 rows=[x for x in ev if x[4]>origin];assert rows[-1][1:4]==[1,0x6058,90]
 records=[];payload=bytearray();overheads=[0]*5;starts={i:next(x[4] for x in ev if x[0]==i and x[1:3]==[0,0x6001]) for i in range(1,len(jobs)+2)}
 for i,j in enumerate(jobs,1):
  desc=bytes.fromhex(j['descriptor']);data=bytes.fromhex(j['data'])
  if j['typed']:
   kind=2 if desc[0]&2 else desc[0]&1;pos=int.from_bytes(desc[3:5],'little')
  else:kind=desc[1];pos=int.from_bytes(desc[6:8],'little')
  records.append(kind|(pos<<8)|(len(data)<<24));payload+=data
  overheads[kind]=max(overheads[kind],starts[i+1]-starts[i]-len(data)*8)
 # Native record count/data prove this exact profile;not a generalWCET bound.
 budget=rows[-1][4]-origin+512
 assert budget<49104
 for name,values,width in [('records',[len(records)]+records,16),('data',payload,2),('tail',[len(rows)]+[((clock-origin)<<40)|(op<<32)|(addr<<8)|value for case,op,addr,value,clock,line in rows],16),('config',[first_poll-last_view,budget,len(rows)]+overheads,16)]:
  (d/f'spool-{name}{f}.hex').write_text('\n'.join(f'{x:0{width}x}' for x in values)+'\n',newline='\n')
 return dict(frame=f,native=sha(q/'spool.sfc'),events=sha(q/'events.csv'),source_records=len(records),source_bytes=len(payload),staging_control_clocks=overheads,preflight_clocks=first_poll-last_view,tail_clocks=rows[-1][4]-origin,budget_clocks=budget,source_path=str(q))


def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];profiles=[profile(d,f) for f in range(907,a[1]+1)]
 p=d/'joint266_tb.sv';s=p.read_text()
 declarations,tasks=EXTRA.split(' task reset384;',1)
 s=once(s,' localparam realtime MASTER_NS378=MASTER_PERIOD_PS378*0.001;','')
 s=once(s,'reg clk=0;always begin','localparam realtime MASTER_NS378=MASTER_PERIOD_PS378*0.001;\n'+declarations+'\n reg clk=0;always begin')
 s=once(s,' initial begin : bus263',' task reset384;'+tasks+'\n initial begin : bus263')
 s=once(s,' task output_frame;', ' task output_frame;') if ' task output_frame;' in s else s
 s=once(s,'tile_at267=0;active263=1;', 'tile_at267=0;reset384();active263=1;')
 # Typed source reads now finish in WRAM before the existing read receipt.
 s=once(s,'descriptor379(0,n313,position379,token313);dma_window379(n313,0,0);','descriptor379(0,n313,position379,token313);store_begin384(dut.flow.tkind,position379,n313);')
 s=once(s,'  #41904;\n  for(integer i=0;i<n313;i++)begin rd261(24\'h400800+i,byte313);ignore313=call263(5,i,byte313);end',
  '''  if(f>=907)begin #(overhead384[dut.flow.tkind]*MASTER_NS378);end else #41904;
  for(integer i=0;i<n313;i++)begin rd261(24'h400800+i,byte313);store_byte384(byte313);ignore313=call263(5,i,byte313);end
  store_end384();''')
 s=once(s,'  dma_end379(0);','')
 s=once(s,'    dma_window379(n,1,0);','    store_begin384(2,first263,n);')
 s=once(s,'ignore263=call263(6,first263,n/2);#41904;', 'ignore263=call263(6,first263,n/2);if(f>=907)begin #(overhead384[2]*MASTER_NS378);end else #41904;')
 s=once(s,"     rd261(24'h400800+i,val263);", "     rd261(24'h400800+i,val263);store_byte384(val263);")
 s=once(s,'    token261(token263);wr261', '    store_end384();token261(token263);wr261')
 s=once(s,'wait(dut.flow.state!=dut.flow.DMA);dma_end379(1);', 'wait(dut.flow.state!=dut.flow.DMA);')
 # Ordinary325 byte replay remains a conservative service allocation. Pad its
 # total to at least measured383 source service;PPU is deferred to final tail.
 s=once(s,'reg executed267,ppu379;', 'reg executed267,ppu379;integer pad384,native384;')
 s=once(s,"  if(ppu379)dma_window379(dut.flow.chunk_length,2,int'(cpu267[cpu_at267+count267-1][63:40])+32);", '''  pad384=0;
  if(ppu379&&f>=907)begin
   store_begin384(dut.flow.header[1],dut.flow.ppu325,dut.flow.chunk_length);
   native384=8*dut.flow.chunk_length+overhead384[dut.flow.header[1]];
   pad384=native384-int'(cpu267[cpu_at267+count267-1][63:40]);if(pad384<0)pad384=0;
  end''')
 s=once(s,'  start267=$realtime;read267=0;', '  start267=$realtime+pad384*MASTER_NS378;read267=0;')
 s=once(s,'     read267++;', '     if(ppu379&&f>=907)store_byte384(byte267);read267++;')
 s=once(s,'  if(ppu379)dma_end379(2);','  if(ppu379&&f>=907)store_end384();')
 s=once(s,'if(PRESENT378&&f>=PRESENT_FIRST378)display_tail378();', 'if(PRESENT378&&f>=PRESENT_FIRST378)display_spool384();')
 p.write_text(s,newline='\n');shutil.copyfile(ROOT/'tools/probe_nes_spool384.py',d/'probe_nes_spool384.py')
 (d/'manifest384.json').write_text(json.dumps(dict(profiles=profiles,WRAM_bytes=20480,FPGA_RTL_changed=False,ARM_changed=False,cold_prefix_original=True,head381_retained_conservatively=True,source_receipt='WRAM storage only',finalACK='after actual383 PPU service',scope=__doc__),indent=2)+'\n')
 return src,pins
engine.prepare=prepare;engine.__file__=__file__
if __name__=='__main__':engine.main()
