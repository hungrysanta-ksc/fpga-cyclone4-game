"""Check a13-record final bank while prior tiles still own both bulk slots."""
import argparse,json
from pathlib import Path
import check_nes_bg675_rtl as base
from nes_raw506 import once

LARGE=r'''task large676;
 reg [7:0] tx[0:94],v,c8;reg [15:0] c16;
 tx[0]='he9;tx[1]=87;tx[2]=0;tx[3]=13;
 for(int j=0;j<12;j++)begin
  tx[4+j*7]='h80;tx[5+j*7]=GEN643;tx[6+j*7]=0;
  tx[7+j*7]=12+j*3;tx[8+j*7]=0;tx[9+j*7]=10+j;tx[10+j*7]=0;
 end
 tx[88]='h83;tx[89]=GEN643;tx[90]=0;c16='hffff;
 for(int i=4;i<91;i++)begin
  c16=c16^{tx[i],8'd0};repeat(8)c16=c16[15]?(c16<<1)^16'h1021:c16<<1;
 end
 tx[91]=c16[15:8];tx[92]=c16[7:0];c8=0;
 for(int i=0;i<93;i++)c8=crc8_197(c8,tx[i]);
 tx[93]=c8;tx[94]='ha5;
 begin197();foreach(tx[i])byte197(tx[i],v);end197();
endtask
task consume676;
 for(int i=0;i<16;i++)begin
  @(negedge host);addr='h400800+i;rd_n=0;repeat(8)@(negedge host);
  if(oe!==0 || dout!==0)$fatal(1,"abort setup read");rd_n=1;repeat(8)@(negedge host);
 end
 for(int i=0;i<4;i++)write_bus('h604c+i,rx197[14+i]);
 write_bus('h6050,'ha5);status197();
endtask
'''

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('bin','board','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    base.BODY=once(base.BODY,'task start675;',LARGE+'task start675;')
    base.BODY=once(base.BODY,'tile<4','tile<16')
    base.BODY=once(base.BODY,"batch('h83,GEN643,0);status197();","large676();status197();")
    base.BODY=once(base.BODY,'start675();pair675();stop675();',
        'start675();pair675();status197();consume676();consume676();if(rx197[3]!==1)$fatal(1,"abort grant");large676();status197();if(rx197[5]!==3||hf||nf)$fatal(1,"abort admission");stop675();')
    base.BODY=once(base.BODY,'PASS675 held zero + BG grant, four ordered receipts, STOP pending, cold restart',
        'PASS675/676 large final bank,16 ordered receipts,STOP pending large bank,cold restart')
    # Keep the original token assertion after acceptance. End may remain
    # undecoded until all preceding tiles have retired; no early end flag.
    result=base.check(a)
    result.update(receipts=16,final_bank_records=13,held_tile_final_bank=True,
        scope='Actual fitted665 endpoint;13-record final bank admitted while earlier tile held.16 ordered read/receipt completions; STOP/cold tests inherited. BG ROM responses modeled, no PPU/physical timing claim.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
