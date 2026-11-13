"""Extend689 real SPI/host boundary checks for the pre-accept E1 snapshot.

The reference keeps old MISO on E1; all acceptance/retirement/SNES controls
remain clock-identical. Expected response is independently captured from the
reference BEFORE E1 acceptance, including ACK/STOP races and19B fallback.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

CHECK=r'''
 reg [7:0] expected709[1:19];integer e1_checked709=0;
 always @(negedge clk)if(!reset && dut.endpoint.progress && dut.endpoint.enable && !dut.endpoint.fault)
  if(dut.endpoint.used!=0||!dut.endpoint.ack_valid||dut.endpoint.checking)$fatal(1,"progress qualification invariant");
 always @(posedge clk)if(!reset && !reference.endpoint.ss[1] && reference.endpoint.sck[1] &&
     !reference.endpoint.prev_sck && reference.endpoint.bit_count==7 && reference.endpoint.byte_count==0)begin
  expected709[1]=8'hf7;
  expected709[2]=reference.endpoint.flags;
  expected709[3]=reference.endpoint.accepted[15:8];expected709[4]=reference.endpoint.accepted[7:0];
  expected709[5]=reference.endpoint.retired[15:8];expected709[6]=reference.endpoint.retired[7:0];
  for(int x=0;x<12;x++)expected709[7+x]=reference.endpoint.ack_valid?reference.endpoint.ack_work[x*8+:8]:0;
  expected709[19]=0;for(int x=1;x<19;x++)expected709[19]=c8(expected709[19],expected709[x]);
 end
'''

RACE=r'''
  // E1 is a pre-accept snapshot even when the prior head retires mid-payload.
  restart();prepare(0);transfer(19);
  begin
   reg [7:0] oldack[0:11];reg [15:0] crc;
   for(int x=0;x<12;x++)oldack[x]=ack[x];
   prepare(1);head[12]=240;tx[0]='he1;crc=c16('hffff,tx[0]);
   for(int x=0;x<256;x++)begin tx[x+1]=x<16?head[x]:x*13;crc=c16(crc,tx[x+1]);end
   tx[257]=crc[15:8];tx[258]=crc[7:0];
   for(int x=0;x<12;x++)ack[x]=oldack[x];
   fork transfer(259);begin #16000;publish();end join
   if(rx[4]!=1||rx[6]!=0||dut.endpoint.accepted!=2||dut.endpoint.retired!=1)$fatal(1,"E1 pre-accept/retire race");
   prepare(1);publish();expect_flags(2);
  end
  // STOP cannot alter a captured E1 status or turn it into new acceptance proof.
  prepare(2);head[12]=1;
  begin
   reg [15:0] crc;crc=c16('hffff,'he1);tx[0]='he1;
   for(int x=0;x<16;x++)begin tx[x+1]=head[x];crc=c16(crc,tx[x+1]);end
   tx[17]='h37;crc=c16(crc,tx[17]);tx[18]=crc[15:8];tx[19]=crc[7:0];
   fork transfer(20);begin #16000;stop=1;end join
   if(rx[4]!=2||rx[6]!=2||rx[7]!=0)$fatal(1,"E1 STOP snapshot");
   stop=0;publish();expect_flags(2);
  end
'''

def run(a):
    src=Path('tools/check_nes_status689_rtl.py').read_text()
    inject=r"""
    s=once(s,'  if(selected&&miso!==miso_ref)$fatal(1,"SPI bit differs");',
        '  if(selected&&reference.endpoint.command==8\'he0&&miso!==miso_ref)$fatal(1,"E0 bit differs");')
    s=s.replace(' integer checks=0;', ' integer checks=0;'+CHECK)
    s=once(s,'  #2000;ss=1;#2000;','''  #2000;ss=1;#2000;
  if(tx[0]==8'he1)begin
   for(int x=1;x<size&&x<=19;x++)if(rx[x]!==expected709[x])$fatal(1,"E1 response byte %0d got%02x want%02x",x,rx[x],expected709[x]);
   e1_checked709++;
  end''')
    s=once(s,'  // STOP cannot tear an already captured response',RACE+'  // STOP cannot tear an already captured response')
    s=s.replace('$display("PASS689 checks=', '$display("PASS709 E1=%0d checks=').replace('checks,compared,PHASE,HALF);$finish;', 'e1_checked709,checks,compared,PHASE,HALF);$finish;')
"""
    # Execute the checked-in legacy generator with explicit localized bench changes.
    # Keep generated source and logs as the authoritative run artifact.
    src=src.replace('status689_tb','credit709_tb').replace("'PASS689'","'PASS709'").replace("r'PASS689", "r'PASS709")
    at="    (a.out/'credit709_tb.sv').write_text(s,newline='\\n')"
    src=once(src,at,inject+'\n'+at)
    ns={'__name__':'credit709_generator','CHECK':CHECK,'RACE':RACE}
    exec(compile(src,'derived_check689_for709','exec'),ns);ns['prepare'](a)
    r=json.loads((a.out/'result.json').read_text());r['stage']=709;r['scope']=__doc__
    r['generator_pins']={n:sha(Path('tools')/n) for n in ('check_nes_status689_rtl.py','check_nes_credit709_rtl.py')}
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('bin','base','board','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
