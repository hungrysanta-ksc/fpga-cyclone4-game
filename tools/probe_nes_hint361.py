# SPDX-License-Identifier: MIT
"""EA receiver on real shared SPI; replay measured M4 hint calls during source input."""
import json,shutil,os,sys
import probe_nes_hint360 as previous
from nes_hint361 import apply
from nes_delta231 import BASE,ROOT,sha,once
engine=previous.engine
old_prepare=engine.prepare
def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0];apply(d)
 arm=BASE/'probes/nes-hint360/arm03/result.json';r=json.loads(arm.read_text());assert r['passed'];w=r['rows'][2]
 packet=bytes.fromhex(w['packets'][0]['hex']);assert len(packet)==24
 (d/'hint361.hex').write_text(' '.join(f'{v:02x}' for v in packet)+'\n');pins[str(arm)]=sha(arm)
 (d/'hint-run361.py').write_text(f'import sys,runpy\nsys.path.insert(0,{str(ROOT / "tools")!r})\nrunpy.run_path({str(ROOT / "tools/run_nes_hint361.py")!r},run_name="__main__")\n',encoding='utf-8')
 (d/'hint361.cmd').write_text(f'@"{sys.executable}" -X utf8 hint-run361.py --job "{d}" >hint-arm361.log 2>&1\n',encoding='ascii')
 p=d/'nes_chr_cache192.sv';s=p.read_text().replace('wire pending=state==WAIT;','wire pending=state==WAIT;wire hit=state==HIT;wire hit_reply=state==REPLY;');p.write_text(s,newline='\n')
 p=d/'joint266_tb.sv';s=p.read_text();s=once(s,'nes_plan_rom267 planrom(', "nes_plan_rom267 planrom(.prelease361(owned&&geometry_valid&&!test_drop),.epoch361(32'd1),.serial361(serial),")
 # Old cache's ready-gated request probe is invalid for the sequential cache.
 # Check the actual physical grant and returned core data instead.
 a0=s.index('   if(qualify267&&core_req267&&planrom.source.cache_path.cache.live&&');b0=s.index('\n   end',a0)+len('\n   end')
 s=s[:a0]+s[b0:]
 s=once(s,'  if(core_response267)begin', '''  if(core_req267&&planrom.mr&&planrom.mready)begin
   core_block267++;
   if(planrom.ma!==22'h001234)$fatal(1,"core priority physical grant361");
  end
  if(core_response267)begin''')
 s=once(s,' integer hf337;', '''
 reg [7:0] hint361[0:23];reg sent361=0;reg [31:0] hint_cost361[0:1];integer hint_file361,hint_result361;
 task send_hint361;
  begin
   hint_file361=$fopen("hint-block361.hex","w");
   for(integer j=13;j<13+length;j++)$fwrite(hint_file361,"%02x ",rx[j]);
   $fclose(hint_file361);
   hint_result361=$system("hint361.cmd");if(hint_result361!=0)$fatal(1,"actual ARM hint producer361");
   $readmemh("hint361.hex",hint361);$readmemh("hint-cost361.hex",hint_cost361);
   if(hint_cost361[1]!=source_cost280[token])$fatal(1,"hint source decode cost changed");
   #(CPI*hint_cost361[0]*1000.0/84.0);
   // Measured actual233 handler body; exception entry/exit is an allocation.
   #(CPI*66*1000.0/84.0+24*1000.0/84.0);
   $fwrite(events261,"hint_start361,%0d,%0t\\n",hf337,$time);
   #2000;ss=0;#2000;
   for(integer j=0;j<24;j++)for(integer b=7;b>=0;b--)begin
    mosi=hint361[j][b];#190.476190476;sck=1;#190.476190476;sck=0;
   end
   #2000;ss=1;#2000;wirebytes+=24;
   $fwrite(events261,"hint_end361,%0d,%0t\\n",hf337,$time);
  end
 endtask
 always @(posedge clk)if(planrom.hfinished361)$fwrite(events261,"hint_fill361,%0d,%0t\\n",hf337,$time);
 integer hf337;''')
 s=once(s,'     #(source_cost280[token]*CPI*1000.0/84.0);', '''     #(source_cost280[token]*CPI*1000.0/84.0);
     if(hf337==907&&!sent361)begin sent361=1;send_hint361();end''')
 p.write_text(s,newline='\n')
 for n in ('nes_hint361.py','probe_nes_hint361.py','nes_cache360.py','run_nes_hint361.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 return src,pins
engine.prepare=prepare
old_call=engine.ARM296.call
def call(self,name,args):
 answer=old_call(self,name,args)
 if name=='commit285' and answer:
  (self.endpoint.d/'hint-prior361.bin').write_bytes(bytes(self.uc.mem_read(0x20000000,0x40000)))
 return answer
engine.ARM296.call=call
engine.__file__=__file__
if __name__=='__main__':engine.main()
