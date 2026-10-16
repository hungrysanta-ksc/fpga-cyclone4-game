# SPDX-License-Identifier: MIT
"""New203 exporter with selected board collector/201 overlap and retire.

No old fill instance or fill/query mux. PPU, source epoch and final display are
fixtures; bulk contains zero tiles only. Not full board or BG/OBJ source proof.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_metadata203 import ROOT,BASE,sha,replace

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=BASE/'probes/nes-capture201/test12';new=BASE/'probes/nes-metadata203/test04';pins={}
 prior=json.loads((old/'result.json').read_bytes());prep=json.loads((new/'preparation203.json').read_bytes())
 def copy(f):
  pins[f.relative_to(BASE).as_posix()]=sha(f);shutil.copyfile(f,a.out/f.name)
 names=[]
 for f in sorted(old.glob('*.sv')):
  if f.name in ('bench.sv','nes_native_fill165.sv','nes_native_export181.sv'):continue
  # Verify selected archived sources, not an arbitrary loose file.
  assert sha(f) in prior['source_pins'].values(),f.name;copy(f);names.append(f.name)
 f=new/'nes_native_export203.sv';assert sha(f)==prep['generated'][f.name];copy(f);names.append(f.name)
 copy(old/'spi200_bus.svh')
 f=old/'bench.sv';assert sha(f)==prior['bench_sha256'];pins[f.relative_to(BASE).as_posix()]=sha(f);s=f.read_text()
 s=replace(s,'module capture201_tb;','module metadata203_capture_tb;')
 start=s.index('wire native_fill_start');end=s.index('wire [2:0] native_patch_count181;',start)
 s=s[:start]+'''wire native_arbiter_fault=0;
wire native_frame_response,native_frame_hit;
wire [63:0] native_frame_data;
wire native_frame_query=inspect?1'b1:native_query;
wire [2:0] native_frame_query_kind=inspect?inspect_kind:native_query_kind;
wire [12:0] native_frame_query_index=inspect?inspect_index:native_query_index;
wire [15:0] native_frame_query_generation=inspect?native_generation:native_query_generation;
assign native_response=native_frame_response;
assign native_hit=native_frame_hit;
assign native_data=native_hit?native_frame_data:64'd0;
'''+s[end:]
 start=s.index('nes_native_fill165 #');end=s.index('wire [3:0] native_export_state177;',start);s=s[:start]+s[end:]
 s=s.replace('nes_native_export181 #','nes_native_export203 #')
 start=s.index('.fill_start(');end=s.index(' .tx_valid(native_tx_valid)',start);s=s[:start]+'\n'+s[end:]
 s=s.replace('capture201_join.svh','metadata203_join.svh');assert 'native_fill' not in s
 (a.out/'bench.sv').write_text(s,encoding='utf8',newline='\n')
 f=old/'capture201_join.svh';pins[f.relative_to(BASE).as_posix()]=sha(f);s=f.read_text()
 start=s.index('reg memory_response=');end=s.index('reg ack=0;',start);s=s[:start]+s[end:]
 s='\n'.join(l for l in s.splitlines() if 'memory_response<=native_fill_request' not in l and 'if(native_fill_request)' not in l)+'\n'
 s=s.replace('0:begin begins++;chr_ended201=0;end',"0:begin if(native_tx_data[63:48]!=16'h2031)$fatal(1,\"wrong version\");begins++;chr_ended201=0;end")
 s=s.replace('if(native_tx_valid&&native_tx_ready)begin','if(native_tx_valid&&native_tx_ready)begin\n   if(native_tx_data[95:93]==6)$fatal(1,"legacy CHR record");')
 s=s.replace('PASS CAPTURE201','PASS METADATA203CAPTURE').replace('// Actual collector/fill/export instances above come from the selected board.', '// Selected board collector + new203 exporter; no fill instance.')
 assert 'native_fill' not in s
 (a.out/'metadata203_join.svh').write_text(s,encoding='utf8',newline='\n')
 for tool,args in [('vlib',['work']),('vlog',['-sv',*names,'bench.sv']),('vsim',['-c','work.metadata203_capture_tb','-gSPI_HALF=190.476190476','-gSPI_SETUP=2000','-gSPI_HOLD=2000','-gSPI_GAP=4000','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (a.out/(tool+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(a.out/(tool+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-5000:]
 match=re.search(r'PASS METADATA203CAPTURE checks=(\d+) commits=3 raw_exported=512 overlapped_capture=1 rejections=1 source_faults=1',text);assert match
 r=dict(passed=True,checks=int(match[1]),commits=3,raw_pixels=512,no_fill_instance=True,source_pins=pins,script_sha256=sha(Path(__file__)),
        bench_sha256=sha(a.out/'bench.sv'),join_sha256=sha(a.out/'metadata203_join.svh'),scope=__doc__,physical=False,new_fit=False)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(match[0])
if __name__=='__main__':main()
