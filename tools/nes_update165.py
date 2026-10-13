# SPDX-License-Identifier: MIT
"""Local command capture and exact terminal predicate; no transaction latency change."""
from pathlib import Path
import argparse,json,difflib,shutil,re
from nes_game147 import ROOT,sha

def spi(s):
 assert len(re.findall(r'(?<!\w)command<=0;',s))==2 and s.count('command<=incoming;')==1
 s=re.sub(r'(?<!\w)command<=0;','',s).replace('command<=incoming;','')
 s=s.replace(' wire [4:0] body_causes;', ' reg offset_zero_command,offset_length_command;\n wire [4:0] body_causes;',1)
 a="(cmd60 && offset!=0) ||\n  ((cmd61 || cmd62 || cmd63 || cmd64) && offset!={5'd0,loaded_bytes})"
 assert s.count(a)==1
 s=s.replace(a,"(offset_zero_command && offset!=0) ||\n  (offset_length_command && offset!={5'd0,loaded_bytes})")
 marker=' // C1 validates and decodes the command.'
 logic=''' // Decode only command kind on the same first-byte edge as command.
 // Offset, live length, ready and faults still use their original edges.
 wire command_first_byte=!ss_sync[1] && sck_sync[1] && !sck_previous && bit_count==7 && byte_count==0;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin command<=0;offset_zero_command<=0;offset_length_command<=0;end
  else if(ss_sync[1])begin command<=0;offset_zero_command<=0;offset_length_command<=0;end
  else if(command_first_byte)begin
   command<=incoming;
   offset_zero_command<=incoming==8'h60;
   offset_length_command<=incoming==8'h61 || incoming==8'h62 || incoming==8'h63 || incoming==8'h64;
  end
 end
'''
 assert s.count(marker)==1
 return s.replace(marker,logic+marker)

def loader(s):
 a=s.index(' always @(posedge mem_clk or posedge reset)begin\n  if(reset)remaining<=0;')
 b=s.index(' task automatic advance_phase;',a)
 block=''' // Always equals (remaining == 1), including pause, drain and reset.
 reg terminal;
 always @(posedge mem_clk or posedge reset)begin
  if(reset)begin remaining<=0;terminal<=0;end
  else if(active_reset)begin remaining<=0;terminal<=0;end
  else if(!timed_phase)begin remaining<=CW'(SETUP_CYCLES);terminal<=(CW'(SETUP_CYCLES)==1);end
  else if(phase_step)begin
   if(!terminal)begin remaining<=remaining-1'b1;terminal<=(remaining==2);end
   else case(state)
    SETUP:begin remaining<=CW'(WRITE_CYCLES);terminal<=(CW'(WRITE_CYCLES)==1);end
    WRITE:begin remaining<=CW'(HOLD_CYCLES);terminal<=(CW'(HOLD_CYCLES)==1);end
    HOLD:begin remaining<=CW'(RELEASE_CYCLES);terminal<=(CW'(RELEASE_CYCLES)==1);end
    default:;
   endcase
  end
 end
'''
 return (s[:a]+block+s[b:]).replace('remaining==1','terminal').replace('remaining!=1','!terminal')

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 for n,fn in [('nes_rom_spi.sv',spi),('nes_rom_loader.sv',loader)]:
  old=(baseline/n).read_text();new=fn(old);(out/n).write_text(new)
  (out/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_spi.sv','nes_rom_loader.sv'],public_sources={'tools/nes_update165.py':sha(Path(__file__))})
 assert set(n for n,h in r['sources'].items() if h!=m['sources'][n])==set(r['changed'])
 (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
