# SPDX-License-Identifier: MIT
"""Actual common SPI: two-bank exchange, partial read, token/gen, STOP, queue/plan."""
import inspect
import guard_nes_spi270 as old
from nes_delta231 import ROOT,once


def testbench():
    s=old.TB.replace('[48:0] link','[106:0] link')
    s=once(s,' integer checks=0,',""" reg src_clk=0;always #22.727 src_clk=~src_clk;
 reg stop280=0,record_valid280=0,byte_valid280=0,flush280=1;reg [7:0] byte280=0,length280=0;
 wire record_ready280,byte_ready280,crc_pending280;wire [15:0] previous280;wire [7:0] crc_byte280;
 integer checks=0,""")
    s=s.replace('source(.link270','source(.frame_generation(16\'d1),.link270')
    s=s.replace(".crc_result(16'd0),.crc_pending(),.crc_previous(),.crc_byte(),",
                '.crc_result(crc16(previous280,crc_byte280)),.crc_pending(crc_pending280),.crc_previous(previous280),.crc_byte(crc_byte280),')
    s=s.replace('.src_clk(clk),.host_clk(clk),.reset(reset),.abort_source(1\'b0),.record_valid(1\'b0),.record_ready(),.record_length(8\'d0),.record_flush(1\'b0),',
        '.src_clk(src_clk),.host_clk(clk),.reset(reset),.abort_source(stop280),.record_valid(record_valid280),.record_ready(record_ready280),.record_length(length280),.record_flush(flush280),')
    s=s.replace(".byte_valid(1'b0),.byte_ready(),.byte_data(8'd0)",'.byte_valid(byte_valid280),.byte_ready(byte_ready280),.byte_data(byte280)')
    s=s.replace('begin ss=1;sck=0;mosi=0;reset=1;retire=0;',
        'begin ss=1;sck=0;mosi=0;reset=1;retire=0;stop280=0;record_valid280=0;byte_valid280=0;')
    a=s.index(' task dcommand(');b=s.index(' task packet;',a)
    s=s[:a]+(ROOT/'tools/nes_spi280_guards.inc').read_text()+s[b:]
    a=s.index('  clear();dcommand(');b=s.index('  clear();@(negedge clk);queue.accepted',a)
    s=s[:a]+'''  source_tests280();
  clear();tx[0]=8'he2;transfer(9,0);check_status(9,8'hf9);
  tx[0]=8'he8;transfer(20,0);check_status(20,8'hd7);
  tx[0]=8'he0;mutate=1;transfer(24,0);mutate=0;check_status(24,8'hf8);
  for(integer i=7;i<23;i++)if(rx[i]!==i-6)$fatal(1,"snapshot changed");checks++;
'''+s[b:]
    a=s.index("  clear();dcommand(8'hd0)");b=s.index("  clear();tx[0]=8'he9",a);s=s[:a]+s[b:]
    return s.replace('PASS SPI270','PASS SPI280').replace('#5000000;','#20000000;')


def main():
    ns=dict(old.__dict__);ns.update(TB=testbench(),__file__=__file__,__doc__=__doc__)
    code=inspect.getsource(old.main).replace('PASS SPI270','PASS SPI280')
    exec(compile(code,'spi280-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
