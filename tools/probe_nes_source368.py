# SPDX-License-Identifier: MIT
"""Fixed-start and continuous source foreground with frontier completion/CRC."""
import json,shutil,sys
observe_last='--observe-last' in sys.argv
if observe_last:sys.argv.remove('--observe-last')
no_bitmap='--no-bitmap' in sys.argv
if no_bitmap:sys.argv.remove('--no-bitmap')
baseline_arm='--baseline-arm' in sys.argv
if baseline_arm:sys.argv.remove('--baseline-arm')
fixed='--fixed-start' in sys.argv
if fixed:sys.argv.remove('--fixed-start')
import probe_nes_hint367 as previous
from nes_source368 import apply,compile_arm
from nes_delta231 import ROOT,sha,once
engine=previous.engine;old_prepare=engine.prepare;old_build=engine.build_rom

class ARM368(previous.ARM367):
 def hook(self,uc,address,size,user):
  if address==(self.symbols['source_hint367']&~1):
   serial=int.from_bytes(uc.mem_read(self.symbols['receiver280']+4,4),'little')
   if serial>=3:
    index=getattr(self,'snapshot368',0)+1;self.snapshot368=index
    (self.endpoint.d/f'causal368-{serial}-{index}.bin').write_bytes(bytes(uc.mem_read(0x20000000,0x40000)))
  super().hook(uc,address,size,user)
previous.ARM367=ARM368

def prepare(*a,**k):
 src,pins=old_prepare(*a,**k);d=a[0]
 if no_bitmap:
  from nes_capture368 import functional,COMMON
  functional(d)
  for name in COMMON:
   if name not in src:src.append(name)
   pins['shared368/'+name]=sha(d/name)
 p=d/'joint266_tb.sv';s=p.read_text()
 s=once(s,' task clear_output;', '''
 reg retired_q368=0;integer retired_count368=0;
 always @(posedge clk)begin
  if(reset)begin retired_q368<=0;retired_count368<=0;end
  else begin
   retired_q368<=flow_retired;
   if(flow_retired&&!retired_q368)begin
    if(captured_generation365!=retired_count368+1)$fatal(1,"duplicate/out-of-order actual retire368");
    retired_count368<=retired_count368+1;
    $fwrite(events261,"retired368,%0d,%0t\\n",captured_generation365,$time);
   end
  end
 end
 task clear_output;''')
 s=once(s,'wait(flow_retired);','wait(retired_count368>=f-904);')
 s=once(s,' task clear_output;', '''
 wire input_phase368=frame.started&&!waiting_display;
 clocking core_audit368 @(posedge clk);
  default input #1step;
  input reset,core_req267,core_response267,input_phase368;
 endclocking
 reg core_pending368=0,core_input368=0;
 integer core_requests368=0,core_replies368=0,input_requests368=0,input_replies368=0;
 always @(core_audit368)begin
  if(core_audit368.reset)begin
   core_pending368=0;core_input368=0;core_requests368=0;core_replies368=0;input_requests368=0;input_replies368=0;
  end else begin
   if(core_audit368.core_response267)begin
    if(!core_pending368)$fatal(1,"ROM response without accepted request368");
    core_pending368=0;core_replies368++;
    if(core_input368)input_replies368++;
   end
   if(core_audit368.core_req267)begin
    if(core_pending368)$fatal(1,"duplicate outstanding ROM request368");
    core_pending368=1;core_input368=core_audit368.input_phase368;core_requests368++;
    if(core_input368)input_requests368++;
   end
  end
 end
 final $display("ROM368 requests=%0d replies=%0d pending=%0d input_requests=%0d input_replies=%0d input_pending=%0d",core_requests368,core_replies368,core_pending368,input_requests368,input_replies368,core_pending368&&core_input368);
 task clear_output;''')
 if observe_last:
  s=once(s,'if(!capture_begin)$fatal', 'if(!capture_begin&&free_id367!=last+1)$fatal')
  s=once(s,'if(missed367||attempts367!=last-906)$fatal', '''if(missed367)begin
     while(!bridge267(8,0,0))#1000;
    end
    if(missed367||attempts367!=last-906)$fatal''')
 p.write_text(s,newline='\n')
 p=d/'nes_bridge267.c';s=p.read_text()
 # Verification-only end-of-run rendezvous, outside measured frame completion.
 needle='int bridge267(int op, int a, int b)'
 if needle not in s:
  import re
  match=re.search(r'int bridge267\([^)]*\)\s*\{',s);assert match;s=s[:match.end()]+'''\n if(op==8){FILE *end368=fopen("arm-result.json","r");if(!end368)return 0;fclose(end368);return 1;}'''+s[match.end():]
 else:
  s=once(s,needle+' {',needle+' {\n if(op==8){FILE *end368=fopen("arm-result.json","r");if(!end368)return 0;fclose(end368);return 1;}')
 p.write_text(s,newline='\n')
 if fixed:
  p=d/'joint266_tb.sv';s=p.read_text()
  # Predeclared existing367 capture phase, not chosen after seeing a result.
  # Readiness cannot move this boundary: late startup is a failure.
  s=once(s,'if(f>=908)begin', '''if(f==907)begin
    while(romcycle267<5371247)@(negedge clk);
    if(romcycle267!=5371247)$fatal(1,"startup missed fixed capture368");
   end
   if(f>=908)begin''')
  p.write_text(s,newline='\n')
 for n in ('nes_source368.c','nes_source368.py','probe_nes_source368.py','nes_capture368.py'):
  shutil.copyfile(ROOT/'tools'/n,d/n);pins[n]=sha(d/n)
 (d/'manifest368.json').write_text(json.dumps(dict(baseline_ARM=baseline_arm,fixed_capture907=5371247 if fixed else None,
  no_bitmap=no_bitmap,new_RTL=no_bitmap,observe_last=observe_last,retire_history=True,shared_boundary={n:sha(d/n) for n in (COMMON if no_bitmap else previous.COMMON)}),indent=2)+'\n',newline='\n')
 return src,pins

def build(d):
 old_build(d);shutil.copyfile(d/'output.elf',d/'pre368-output.elf')
 if not baseline_arm:apply(d);compile_arm(d)

engine.prepare=prepare;engine.build_rom=build;engine.__file__=__file__
if __name__=='__main__':engine.main()
