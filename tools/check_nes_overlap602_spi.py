"""Test a second D1 before credit, and a four-byte D2 with separate retirement confirmation."""
import argparse
from pathlib import Path
from types import SimpleNamespace

from check_nes_wire600 import GENERATIONS, ROOT, pin, read
from nes_raw506 import once
from test_nes_transfer512_spi import prepare, run


def main(a):
    old=read(ROOT/'analysis/wire600-verification.json')
    for name,variant in [('legacy','legacy'),('shared','shared'),('short','shared')]:
        rtl=a.probe/variant/'nes_native_spi165.sv'
        pin(rtl,old['RTL'][variant])
        out=a.out/name
        prepare(SimpleNamespace(out=out,records=a.probe/'records.csv',rtl=rtl,legacy=variant=='legacy'),GENERATIONS)
        tb=(out/'tb.sv').read_text()
        tb=once(tb,'reg got_end,got_commit;', 'reg [7:0] first_read[0:258]; reg got_end,got_commit;')
        tb=once(tb,'crc=16\'hffff;for(pos=1;',"""for(pos=0;pos<length+3;pos++)first_read[pos]=rx[pos];
      trace_on=0;transfer(length+3);trace_on=1;
      for(pos=0;pos<length+3;pos++)if(rx[pos]!==first_read[pos])$fatal(1,"D1 advanced without POP");
      if(!dut.sealed||ready||dut.token!=token||!dut.read_seen)$fatal(1,"owner changed");
      crc=16'hffff;for(pos=1;""")
        if name=='short':
            # D2 is committed on chip-select release only. D0 still confirms the new token.
            s=rtl.read_text()
            s=once(s,"else if(byte_count!=8", """else if(command==8'hd2)begin
      if(fault||byte_count!=4||bit_count!=0||tail!=request_crc||!sealed||!read_seen||
         offset[15:0]!=token)fault<=1;
      else begin sealed<=0;read_seen<=0;used<=0;block_crc<=16'hffff;token<=token+1'b1;end
     end else if(byte_count!=8""")
            start=s.index("      8'hd2:if(")
            s=s[:start]+s[s.index("      8'hd3:",start):]
            # Override the receive fields on D2, leaving D0/D3 byte decoding untouched.
            needle='if(incoming==8\'hd1)read_seen<=0;end'
            assert needle in s
            # Last case is the MOSI decoder. CRC is updated elsewhere in it.
            pos=s.rindex('case(byte_count)')
            end=s.index('endcase',pos)+len('endcase')
            s=s[:end]+"""
     if(command==8'hd2 && byte_count!=0)begin
      if(byte_count<=2)begin offset<={offset[15:0],incoming};request_crc<=crc8(request_crc,incoming);end
      else if(byte_count==3)begin offset<=offset;tail<=incoming;request_crc<=request_crc;end
     end
"""+s[end:]
            (out/rtl.name).write_text(s)
            tb=once(tb,"request(8'hd2,token,0);transfer(8);status_check;", """tx[0]=8'hd2;tx[1]=token[15:8];tx[2]=token[7:0];tx[3]=c8(c8(c8(0,tx[0]),tx[1]),tx[2]);
      transfer(4);if(fault)$fatal(1,"short POP");""")
            bad="""reset=1;#100;reset=0;#100;
   @(negedge clk);data=records[count-1];valid=1;@(posedge clk);@(negedge clk);valid=0;wait(dut.sealed);
   tx[0]=8'hd1;transfer(dut.used+3);
   tx[0]=8'hd2;tx[1]=0;tx[2]=TOKEN;tx[3]=c8(c8(c8(0,tx[0]),tx[1]),tx[2])^BAD;
   transfer(SIZE);if(!fault||!dut.sealed||dut.token!=0)$fatal(1,"destructive POP");
"""
            tb=once(tb,'$display("PASS SPI165', ''.join(bad.replace('TOKEN',str(tok)).replace('BAD',str(crc)).replace('SIZE',str(n)) for tok,crc,n in [(1,0,4),(0,1,4),(0,0,3),(0,0,5)])+'$display("PASS SPI165')
        (out/'tb.sv').write_text(tb)
        run(SimpleNamespace(out=out,data=a.data,bin=a.bin,legacy=variant=='legacy'),GENERATIONS)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('probe','data','bin','out'):
        p.add_argument('--'+arg,type=Path,required=True)
    main(p.parse_args())
