# SPDX-License-Identifier: MIT
"""Compare210/213 reset-entry ROM responses and actual65816 startup.

Actual selected207 bridge/status RTL exports bus ROM bytes; Mesen boots those
bytes and records ROM reads/milestones, which RTL replays with status73 polls.
Fixed100ns read/150ns write windows, fixture RUN and inactive peer: NOT physical
timing, full board startup, or live clock-coupled ARM/RTL/65816 co-simulation.
"""
from pathlib import Path
import argparse, json, os, re, shutil, subprocess
from nes_runtime213 import ROOT, BASE, sha

TB = r'''
`timescale 1ns/1ps
module startup214;
 reg clk=0,reset=1,active=0,stop=0,ss=1,sck=0,mosi=0;
 reg [23:0] address=0;reg rn=1,wn=1,romsel=1;reg [7:0] din=0;
 wire selected,miso,oe,dir,pc,fault;wire [7:0] dout;wire [15:0] pads;
 nes_sink_bridge165 dut(clk,reset,active,stop,ss,sck,mosi,selected,miso,address,rn,wn,romsel,din,dout,oe,dir,pc,pads,fault);
 reg power_reset=1;
 wire status_receive,status_selected,status_miso;
 nes_screen_status151 status(clk,power_reset,active,address,rn,wn,romsel,din,ss,sck,mosi,status_receive,status_selected,status_miso);
 wire core_reset=reset;
 wire sink_oe204=oe,sink_dir204=dir;wire [7:0] sink_data204=dout;
 wire bus_oe_n=1,bus_dir=0;wire [7:0] bus_data=0;
 wire consumer_oe,consumer_dir;wire [7:0] consumer_data;
 wire SNES_DATABUS_DIR,SNES_DATABUS_OE;wire [7:0] SNES_DATA;
 // TOP_ASSIGNMENTS
 always #5.952 clk=~clk;
 integer fd,outfd,n,a,v,checks=0,reads=0,writes=0;reg [7:0] b,rx[0:7];reg [31:0] op;
 task readbyte(input [23:0] at,input integer expected);
 begin
  address=at;rn=0;wn=1;romsel=0;#100;
  if(SNES_DATABUS_OE||!SNES_DATABUS_DIR||(^SNES_DATA===1'bx))$fatal(1,"ROM undriven %h",at);
  b=SNES_DATA;if(expected>=0&&b!==expected[7:0])$fatal(1,"ROM mismatch %h %h expected%h",at,b,expected);
  checks++;rn=1;romsel=1;#100;
 end endtask
 task query(input integer stage,input integer flags);
 integer x,k;reg [7:0] tx;
 begin
  #2000;ss=0;#2000;
  for(x=0;x<8;x++)begin tx=x==0?8'h73:0;rx[x]=0;
   for(k=7;k>=0;k--)begin mosi=tx[k];#190.476;sck=1;rx[x][k]=status_selected?status_miso:0;#190.476;sck=0;end
  end
  #2000;ss=1;#2000;
  if(rx[1]!==8'he6||rx[2]!==stage[7:0]||rx[4]!==flags[7:0]||rx[7]!==2)$fatal(1,"status stage%0d flags%0d got%h/%h",stage,flags,rx[2],rx[4]);
  checks++;
 end endtask
 initial begin
  #200;power_reset=0;reset=0;#200;
  // RUN withheld reproduces a valid zero status and absent ROM ownership.
  address=24'h00fffc;rn=0;romsel=0;#200;
  if(!SNES_DATABUS_OE)$fatal(1,"inactive drove ROM");rn=1;romsel=1;query(0,0);
  // A non-idle SPI transaction must block admission, then idle permits it.
  ss=0;active=1;#300;address=24'h008000;rn=0;romsel=0;#100;
  if(!SNES_DATABUS_OE)$fatal(1,"mid-SPI admission");rn=1;romsel=1;ss=1;#300;
  // Power-reset diagnostics after the deliberately blocked activity fixture.
  power_reset=1;#100;power_reset=0;#100;
  readbyte(24'h00fffc,0);readbyte(24'h00fffd,128);query(0,7);
  if($test$plusargs("DUMP"))begin
   outfd=$fopen("bus-rom.bin","wb");if(!outfd)$fatal(1,"output");
   for(a=24'h008000;a<=24'h00ffff;a++)begin readbyte(a,-1);$fwrite(outfd,"%c",b);end
   $fclose(outfd);
  end else begin
   fd=$fopen("boot-events.txt","r");if(!fd)$fatal(1,"events");
   while(!$feof(fd))begin
    n=$fscanf(fd,"%s %h %h\n",op,a,v);
    if(n==3)begin
     if(op=="R")begin readbyte(a,v);reads++;end
     else if(op=="W")begin
      address=a;din=v;rn=1;romsel=1;wn=0;#150;
      if(!status_receive||SNES_DATABUS_OE||SNES_DATABUS_DIR)$fatal(1,"status write direction");
      wn=1;#100;writes++;if(a==24'h007000)query(v,7);
     end else $fatal(1,"event kind");
    end
   end
   $fclose(fd);query(3,7);
   active=0;reset=1;#200;query(3,7); // STOP retains evidence.
   if(reads<1000||writes<4)$fatal(1,"missing startup traffic");
  end
  $display("PASS STARTUP214 checks=%0d reads=%0d writes=%0d",checks,reads,writes);$finish;
 end
endmodule
'''

LUA = r'''
local f=assert(io.open(OUT..'/bus-rom.bin','rb'));local rom=f:read('*a');f:close();assert(#rom==32768)
local events=assert(io.open(OUT..'/boot-events.txt','w'))
local stages={};local spc=0;local reads=0
emu.addMemoryCallback(function(a,v)
 local expected=rom:byte(a-0x8000+1);assert(expected==v,'projected ROM differs')
 events:write(string.format('R %06x %02x\n',a,expected));reads=reads+1;return expected
end,emu.callbackType.read,0x8000,0xffff)
emu.addMemoryCallback(function(a,v)
 events:write(string.format('W %06x %02x\n',a,v))
 if a==0x7001 then spc=v end
 if a==0x7000 then
  stages[#stages+1]=v
  if v==3 then
   assert(#stages==3 and stages[1]==1 and stages[2]==2 and spc==0xa9)
   events:close();local o=assert(io.open(OUT..'/boot.json','w'))
   o:write(string.format('{"ready":true,"spc":%d,"reads":%d,"stages":[1,2,3]}',spc,reads));o:close();emu.stop(0)
  end
 end
end,emu.callbackType.write,0x7000,0x7001)
emu.addEventCallback(function()assert(emu.getState().frameCount<300,'boot timeout')end,emu.eventType.endFrame)
'''

def main():
    p=argparse.ArgumentParser()
    for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();assert str(a.out).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    a.out.mkdir(parents=True,exist_ok=False)
    board=BASE/'probes/nes-board207/mapfit02'
    names=['nes_domain_reset124.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv','nes_screen_status151.sv']
    pins={}
    for n in names:shutil.copyfile(board/n,a.out/n);pins[n]=sha(board/n)
    top=(board/'fxpak_nes_screen137_top.sv').read_text();assigns=[]
    for n in ['consumer_oe','consumer_dir','consumer_data','SNES_DATABUS_DIR','SNES_DATABUS_OE','SNES_DATA']:
        match=re.findall(r'assign\s+'+n+r'\s*=.*?;',top,re.S);assert len(match)==1;assigns+=match
    (a.out/'startup214.sv').write_text(TB.replace('// TOP_ASSIGNMENTS','\n'.join(assigns)),encoding='utf8')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    def run(cmd,cwd,label,timeout=90):
        with (cwd/(label+'.log')).open('wb') as f:
            q=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
        t=(cwd/(label+'.log')).read_text(errors='replace')
        assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
        return t
    run([a.questa_bin/'vlib.exe','work'],a.out,'vlib')
    run([a.questa_bin/'vlog.exe','-sv',*names,'startup214.sv'],a.out,'vlog')
    run([a.questa_bin/'vmap.exe','-c'],a.out,'vmap-create')
    run([a.questa_bin/'vmap.exe','work',(a.out/'work').as_posix()],a.out,'vmap')
    results=[]
    for name,client in [('old210',board/'sink-program.hex'),('failed213',BASE/'probes/nes-runtime213/asm01/sink-program.hex')]:
        d=a.out/name;d.mkdir();shutil.copyfile(client,d/'sink-program.hex');shutil.copyfile(a.out/'modelsim.ini',d/'modelsim.ini')
        vsim=[a.questa_bin/'vsim.exe','-c','work.startup214']
        t=run([*vsim,'+DUMP','-do','onerror {quit -code 1}; run -all; quit -f'],d,'dump')
        assert 'PASS STARTUP214' in t
        rom=(d/'bus-rom.bin').read_bytes();compact=bytes.fromhex(client.read_text())
        assert len(rom)==32768 and rom[:0xfc0]==compact[:0xfc0] and rom[0x7fc0:]==compact[0xfc0:]
        assert rom[0xfc0:0x7fc0]==b'\xff'*(0x7fc0-0xfc0)
        (d/'capture.lua').write_text('local OUT='+json.dumps(d.as_posix())+'\n'+LUA,encoding='utf8')
        mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
        shutil.copyfile(d/'bus-rom.bin',d/'startup.sfc')
        run([mesen,'--testRunner',d/'capture.lua',d/'startup.sfc','--timeout=30','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],d,'mesen',45)
        boot=json.loads((d/'boot.json').read_bytes());assert boot['ready']
        t=run([*vsim,'-do','onerror {quit -code 1}; run -all; quit -f'],d,'replay')
        m=re.search(r'PASS STARTUP214 checks=(\d+) reads=(\d+) writes=(\d+)',t);assert m
        r=dict(candidate=name,client_sha256=sha(client),boot=boot,replay=dict(checks=int(m[1]),reads=int(m[2]),writes=int(m[3])))
        results.append(r);print(json.dumps(r),flush=True)
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,cases=results,source_pins=pins,scope=__doc__,physical=False,root_cause_reproduced=False,source_sha256=sha(Path(__file__))),indent=2)+'\n')
if __name__=='__main__':main()
