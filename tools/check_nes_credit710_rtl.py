"""709 interface checks plus aborted command/snapshot reset reconstruction."""
import argparse,json
from pathlib import Path
import check_nes_credit709_rtl as prior
from nes_raw506 import sha

RESET=r'''
  // No snapshot reset is needed only if interrupted responses stay hidden
  // and every new command replaces all bytes before they are observed.
  for(int mode=0;mode<2;mode++)for(int cut=0;cut<4;cut++)begin
   integer bits;
   restart();prepare(0);transfer(19);publish();event_write();expect_flags(10);
   prepare(1);if(mode==0)tx[0]='he0;
   bits=cut==0?3:cut==1?8:cut==2?16:30;
   #2000;ss=0;#2000;
   for(int k=0;k<bits;k++)begin
    mosi=tx[k/8][7-k%8];#(HALF);sck=1;
    if(cut==1&&k==7)begin
     wait(dut.endpoint.crc_busy);#1;reset=1;
    end
    #(HALF);sck=0;
   end
   reset=1;ss=1;sck=0;#1;
   if(selected||selected_ref)$fatal(1,"reset exposed stale snapshot");
   #200;reset=0;#1000;expect_flags(0);
   if(dut.endpoint.accepted||dut.endpoint.retired)$fatal(1,"reset retained credit");
   prepare(0);transfer(19);publish();expect_flags(2);
  end
'''

def run(a):
    prior.RACE=RESET+prior.RACE;prior.run(a)
    p=a.out/'result.json';r=json.loads(p.read_text());r.update(stage=710,scope=__doc__,reset_interrupt_cases_per_run=8)
    r['generator_pins']['check_nes_credit710_rtl.py']=sha(Path(__file__))
    p.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('bin','base','board','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
