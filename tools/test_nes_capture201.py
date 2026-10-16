# SPDX-License-Identifier: MIT
"""Actual selected board capture/fill/export + display-retire source lifetime.

PPU/memory/host display are fixtures. Not full game, C runtime or board SPI mux.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from test_nes_board181_join import bench
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)
def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=BASE/'probes/nes-window184-coupled/evidence/route02'
 names=['nes_native_planes165.sv','nes_native_fill165.sv','nes_native_export181.sv','nes_patch_rows181.sv',
        'nes_patch_capture181.sv','nes_native_compact181.sv','nes_native_raster181.sv','nes_native_mailbox165.sv','nes_domain_reset124.sv']
 files=[board/n for n in names]
 files += [ROOT/'src/nes/rtl'/n for n in ('nes_capture_lease201.sv','nes_plan_batch201.sv','nes_plan_spi200.sv','nes_tile_bulk193.sv','nes_bulk_aperture188.sv','nes_tile191.sv')]
 files += [ROOT/'src/nes/video'/n for n in ('nes_native_frame201.sv','nes_native_capture201.sv')]
 files += [ROOT/'tests/nes-functional'/n for n in ('capture201_join.svh','spi200_bus.svh')]
 pins={f.relative_to(BASE).as_posix():sha(f) for f in files}
 for f in files:shutil.copyfile(f,a.out/f.name)
 s=bench(board);s=s[:s.index('reg memory_response=')]
 s=rep(s,'module board181_join_tb;','module capture201_tb;')
 s=rep(s,'always #5 clk=~clk;','always #23.28 clk=~clk;')
 s=rep(s,'if(!native_frame_owned)$fatal', 'if(scenario!=4&&!native_frame_owned)$fatal')
 # Declarations precede all use; original actual instance/query mux is preserved
 # except the explicit lifetime wrapper, exact start output and inspection port.
 at=s.index('wire native_release_frame')
 s=s[:at]+'''reg inspect=0;reg [2:0] inspect_kind=0;reg [12:0] inspect_index=0;
 wire capture_begin201,lease_fault201,export_release201;
 reg source_ready201=1,source_rom201=1,source_write201=0,reader_drained201=1;
 reg [31:0] epoch201=41;
 wire lease201,waiting201,permit201,retire_commit201,export_permitted201;
 wire [31:0] captured_epoch201;wire [15:0] captured_gen201,eg201;
'''+s[at:]
 s=rep(s,'nes_native_frame181 native_frame(','''nes_native_capture201 native_frame(
 .capture_begin(capture_begin201),.source_ready(source_ready201),.source_is_rom(source_rom201),.source_writing(source_write201),.live_epoch(epoch201),
 .export_error(native_export_error),.reader_drained(reader_drained201),.retire_commit(retire_commit201),.retire_generation(eg201),
 .effective_release(native_release_frame),.lease_valid(lease201),.retire_permitted(permit201),.export_permitted(export_permitted201),.waiting_display(waiting201),.lease_fault(lease_fault201),
 .captured_epoch(captured_epoch201),.captured_generation(captured_gen201),''')
 # Only exporter requests are intercepted; fill/history see effective release.
 start=s.index('nes_native_export181 #');left=s[:start];right=s[start:]
 right=rep(right,'.release_frame(native_release_frame)', '.release_frame(export_release201)')
 right=rep(right,".enable(1'b1)",'.enable(export_permitted201)')
 s=left+right
 start=s.index('nes_native_capture201 native_frame(');end=s.index('nes_native_fill165 #',start)
 s=s[:start]+rep(s[start:end],'.release_frame(native_release_frame)', '.release_frame(export_release201)')+s[end:]
 s=s.replace('native_frame.row_commit','native_frame.frame.row_commit').replace('native_frame.committed_row','native_frame.frame.committed_row').replace('native_frame.row_patched','native_frame.frame.row_patched')
 s=rep(s,'wire [3:0] native_export_error;','')
 s=rep(s,'wire capture_begin201,lease_fault201,export_release201;','wire capture_begin201,lease_fault201,export_release201;wire [3:0] native_export_error;')
 s=rep(s,'native_frame_query=native_fill_busy?', 'native_frame_query=inspect?1\'b1:native_fill_busy?')
 s=rep(s,'native_frame_query_kind=native_fill_busy?', 'native_frame_query_kind=inspect?inspect_kind:native_fill_busy?')
 s=rep(s,'native_frame_query_index=native_fill_busy?', 'native_frame_query_index=inspect?inspect_index:native_fill_busy?')
 s=rep(s,'native_frame_query_generation=native_fill_busy?', 'native_frame_query_generation=inspect?native_generation:native_fill_busy?')
 s+='\n`include "capture201_join.svh"\nendmodule\n'
 (a.out/'bench.sv').write_text(s,encoding='utf8',newline='\n')
 pins[(board/'nes_live_joint.sv').relative_to(BASE).as_posix()]=sha(board/'nes_live_joint.sv')
 for f in (ROOT/'tools/test_nes_board181_join.py',ROOT/'tests/nes-functional/collect181_tb.sv'):
  pins[f.relative_to(BASE).as_posix()]=sha(f)
 env=os.environ.copy();env['PATH']=str(a.questa_bin)+os.pathsep+env.get('PATH','')
 def run(name,args):
  with (a.out/(name+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(name+'.exe')),*args],cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(name+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
  return t
 run('vlib',['work']);run('vlog',['-sv',*[f.name for f in files if f.suffix=='.sv'],'bench.sv'])
 t=run('vsim',['-c','work.capture201_tb','-gSPI_HALF=190.476190476','-gSPI_SETUP=2000','-gSPI_HOLD=2000','-gSPI_GAP=4000','-do','onerror {quit -code 1}; run -all; quit -f'])
 m=re.search(r'PASS CAPTURE201 checks=(\d+) commits=(\d+) raw_exported=512 overlapped_capture=1 rejections=1 source_faults=1',t);assert m and int(m[2])==3
 result=dict(passed=True,checks=int(m[1]),commits=int(m[2]),raw_exported=512,overlapped_capture=1,source_pins=pins,
             script_sha256=sha(Path(__file__)),bench_sha256=sha(a.out/'bench.sv'),physical=False,scope=__doc__)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(m[0])
if __name__=='__main__':main()
