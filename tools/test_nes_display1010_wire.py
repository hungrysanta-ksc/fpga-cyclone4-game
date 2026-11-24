"""Feed both 978 timelines through the real sink packet/receipt, PPU and SPI buses."""
import argparse
import json
from pathlib import Path

from nes_display1010 import ROOT, once

def bench(dest):
    rtl = (ROOT/'tests/nes-functional/tb_nes_frame900.sv').read_text()
    rtl = rtl[:rtl.index(' initial begin')]
    rtl = once(rtl,'tb_nes_frame900','tb_nes_display1010')
    rtl = once(rtl,'wire header,','reg cancel=0,first=0; integer abort_byte=-1; wire header,')
    rtl = once(rtl,'monitor(.clk','monitor(.trace_cancel(cancel || fault),.evt905(3\'b0),.first905(first),.ret905(1\'b0),.units905(8\'d0),.writer903(1\'b0),.reader903(1\'b0),.ready903(1\'b0),.snap903(1\'b0),.kind903(1\'b0),.token903(32\'h13572468),.clk')
    rtl = once(rtl,'snapshot[0:25]','snapshot[0:31]')
    rtl = once(rtl,'for(integer k=1;k<26;k++)octet(0,snapshot[k]);', '''for(integer k=1;k<32;k++)begin
   if(k==abort_byte)cancel=1;
   octet(0,snapshot[k]);
  end''')
    rtl = once(rtl,' integer seq=0;', ''' integer seq=0;
 reg [15:0] stamp[0:4];
 task set_tick(input integer i);
  @(negedge clk);monitor.trace.clock_count={stamp[i],15'b0};
 endtask''')
    for key,i in [("  read_byte('h400000);",1),("   a='h7fe200;",2),
                  ("   a='h2100;",3),("  write_byte('h6010,opcode==3);",4)]:
        rtl = once(rtl,key,'  if(opcode==3)set_tick('+str(i)+');\n'+key)
    rtl+=''' task check_stamps(input integer g);
  if(fault || snapshot[1]!==8'ha1 || {snapshot[3],snapshot[2]}!==g[15:0] ||
     snapshot[30]!==15 || snapshot[31]!==8'ha5)$fatal(1,"row %d %x %x %x %x %x",g,snapshot[1],snapshot[3],snapshot[2],snapshot[30],snapshot[31]);
  for(integer i=0;i<5;i++)if({snapshot[17+2*i],snapshot[16+2*i]}!==stamp[i])
    $fatal(1,"stamp %d %d",g,i);
 endtask
 initial begin
 #130; reset=0;active=1;#1000;
'''
    report=json.loads((ROOT/'analysis/demo-loss1009-results.json').read_bytes())
    for phase,rows in report['replay978'].items():
        rtl+=' active=0;#400;active=1;#1000;seq=0;\n'
        for gen,row in rows.items():
            stamps=[int(row[k])*84000000//(21477272*32768) for k in
                    ('previous_show','SEAL_header','last_dma','show','final_ACK')]
            if gen=='906':
                rtl+=f" stamp[1]=0;stamp[2]=1;stamp[3]={stamps[0]};stamp[4]={stamps[0]};\n"
                rtl+=' packet(905,1,0,0);packet(905,3,0,0);query();if(snapshot[31]!==0)$fatal(1,"cold");\n'
            rtl+=' '+''.join(f'stamp[{i}]={v};' for i,v in enumerate(stamps))+'\n'
            rtl+=f' packet({gen},1,0,0);packet({gen},3,0,0);query();check_stamps({gen});\n'
        rtl+=f' $display("PASS1010 phase {phase} seven same-generation rows");\n'
    rtl+=''' abort_byte=31;query();if(snapshot[31]===8'ha5)$fatal(1,"accepted torn footer");cancel=0;abort_byte=-1;
 packet(913,1,0,0);packet(913,3,0,0);query();if(snapshot[31]!==0)$fatal(1,"STOP history");
 stamp[0]=stamp[3];packet(914,1,0,0);packet(914,3,0,0);query();check_stamps(914);
 @(negedge clk);monitor.trace.clock_count=31'h7fffffff;@(negedge clk);
 query();if(snapshot[31]!==0)$fatal(1,"clock wrap");
 packet(914,1,0,0);packet(914,3,0,0);query();if(snapshot[31]!==0)$fatal(1,"pre-wrap predecessor");
 packet(915,1,0,0);packet(915,3,0,0);query();check_stamps(915);
 @(negedge clk);first=1;@(negedge clk);first=0;query();if(snapshot[31]!==0)$fatal(1,"new supply");
 packet(916,1,0,0);query();if(snapshot[31]!==0)$fatal(1,"partial");
 packet(916,3,0,1);query();if(!fault || snapshot[31]!==0)$fatal(1,"bad receipt");
 $display("PASS1010 cold, interrupted reply, recovery, partial, new supply, invalid identity");$finish;
 end
endmodule
'''
    dest.write_text(rtl,newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    bench(p.parse_args().output)
