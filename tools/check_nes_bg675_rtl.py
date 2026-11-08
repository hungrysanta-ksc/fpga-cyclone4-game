"""Check fitted MMC666 plan credit separately from held zero/BG tile ownership."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from check_nes_fault641 import MODULES,ROOT,digest,evidence
from nes_raw506 import once

BODY=r'''parameter integer GEN643=97;
assign export_drop=0;assign export_reason=0;
task pair675;
 reg [7:0] tx[0:21],v,c8;
 reg [15:0] c16;
 tx[0]='he9;tx[1]=14;tx[2]=0;tx[3]=2;
 for(int j=0;j<2;j++)begin
  tx[4+j*7]='h80;tx[5+j*7]=GEN643;tx[6+j*7]=0;
  tx[7+j*7]=6+j*3;tx[8+j*7]=0;tx[9+j*7]=8+j;tx[10+j*7]=0;
 end
 c16='hffff;
 for(int i=4;i<18;i++)begin
  c16=c16^{tx[i],8'd0};repeat(8)c16=c16[15]?(c16<<1)^16'h1021:c16<<1;
 end
 tx[18]=c16[15:8];tx[19]=c16[7:0];c8=0;
 for(int i=0;i<20;i++)c8=crc8_197(c8,tx[i]);
 tx[20]=c8;tx[21]='ha5;
 begin197();foreach(tx[i])byte197(tx[i],v);end197();
endtask
task start675;
 repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
 gen=GEN643-1;capture_begin=1;@(negedge nes);capture_begin=0;gen=GEN643;owned=1;
 @(negedge nes);release_frame=1;@(negedge nes);release_frame=0;owned=0;
 batch('h82,GEN643,0);status197();
 if(rx197[3]!==1 || rx197[6]!==1 || rx197[8]!==16 || rx197[5]!==1)$fatal(1,"initial E8");
endtask
task stop675;
 reset=1;addr='h400800;rd_n=0;repeat(12)@(negedge nes);
 if(lease||retire||hf||nf||oe!==1||dut.chunk_ready!==0)$fatal(1,"STOP");
 rd_n=1;
endtask
initial begin
 reg [31:0] token;
 reg [159:0] held;
 start675();
 token={rx197[17],rx197[16],rx197[15],rx197[14]};
 pair675();status197();
 if(rx197[5]!==2 || rx197[6]!==1 || token!=={rx197[17],rx197[16],rx197[15],rx197[14]} || hf||nf)$fatal(1,"BG grant changed held token");
 // With no reads, repeated observations cannot consume either tile slot.
 for(int k=0;k<3;k++)begin
  status197();if(rx197[6]!==1 || rx197[8]!==16 || token!=={rx197[17],rx197[16],rx197[15],rx197[14]} || retire)$fatal(1,"unread tile advanced");
 end
 for(int tile=0;tile<4;tile++)begin
  if(tile==2)begin
   if(rx197[3]!==1)$fatal(1,"missing plan credit after two consumed tiles");
   batch('h83,GEN643,0);status197();
   if(rx197[5]!==3 || rx197[6]!==1 || hf||nf)$fatal(1,"END while held");
  end
  if(rx197[8]!==16 || rx197[6]!==1 || {rx197[17],rx197[16],rx197[15],rx197[14]}!==(token+tile))$fatal(1,"ordered token %0d",tile);
  for(int i=0;i<16;i++)begin
   @(negedge host);addr='h400800+i;rd_n=0;repeat(8)@(negedge host);
   if(oe!==0 || dout!==0)$fatal(1,"read");rd_n=1;repeat(8)@(negedge host);
  end
  for(int i=0;i<4;i++)write_bus('h604c+i,rx197[14+i]);
  write_bus('h6050,'ha5);status197();
 end
 if(rx197[6]!==0 || rx197[3]!==2 || hf||nf||lease_fault||!lease||retire)$fatal(1,"premature retire");
 stop675();
 // Abort with two plans admitted and the first tile still wholly unread.
 start675();pair675();stop675();
 start675();stop675();
 $display("PASS675 held zero + BG grant, four ordered receipts, STOP pending, cold restart");$finish;
end
'''

def check(a):
    sof=digest(a.board/'output_files/board.sof')
    assert sof==evidence('trial666-package.json')['board665']['SHA']['board.sof']
    a.out.mkdir(parents=True,exist_ok=False)
    files=['nes_'+m+'.sv' for m in MODULES]
    pins=evidence('entry665-verification.json')['board_inputs']['inputs']
    for f in files:
        assert digest(a.board/f)==pins[f],f
        shutil.copyfile(a.board/f,a.out/f)
    test=ROOT/'tests/nes-functional'
    shutil.copyfile(test/'spi200_bus.svh',a.out/'spi200_bus.svh')
    tb=once((test/'fault641_tb.sv').read_text(),'tx[10]=1;tx[11]=0;','tx[10]=3;tx[11]=0;')
    tb=once(tb,'.mem_data(8\'d0),',".mem_data(8'd0),.bg_word(8'd0),")
    (a.out/'fault641_tb.sv').write_text(tb)
    (a.out/'reject643.svh').write_text(BODY)
    commands=[('vlib',['work']),('vlog',['-sv','+define+WITNESS642+REJECT643',*files,'fault641_tb.sv'])]
    commands += [('vsim'+str(i),['-c','fault641_tb','-gHOST_PHASE='+str(phase),'-gNES_HALF=23.281','-gSPI_HALF=190.476',
                  '-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0']) for i,phase in enumerate((0,8))]
    for name,args in commands:
        tool='vsim' if name.startswith('vsim') else name
        with (a.out/(name+'.log')).open('wb') as log:
            subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        if tool=='vsim':assert 'PASS675' in (a.out/(name+'.log')).read_text()
    return dict(SOF=sof,source_SHA={f:digest(a.out/f) for f in files},phases=[0,8],receipts=4,
        STOP_pending=True,cold_restart=True,scope='Actual board665 endpoint RTL; modeled constant ROM response, no PPU or physical PSRAM timing claim.')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('bin','board','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=check(a);(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
