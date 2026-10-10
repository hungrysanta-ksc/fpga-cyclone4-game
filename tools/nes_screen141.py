# SPDX-License-Identifier: MIT
"""Materialize141 from pinned140: balanced menu budget, actual-consumer deadline, completion and small ROM caches."""
from pathlib import Path
import argparse,json,shutil,re
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def prepare(base,out,kind):
 assert not out.exists();e=base/'nes-response140/evidence'
 meta=json.loads((ROOT/'analysis/response140-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 prefix={'fit':'fit01/','arm':'arm01/','host':'host01/'}[kind];copied={}
 for n,h in pins.items():
  if not n.startswith(prefix):continue
  rel=n[len(prefix):];p=Path(rel)
  if kind=='fit' and (rel.startswith(('db/','incremental_db/','output_files/')) or p.suffix not in ['.sv','.v','.vhd','.hex','.sdc','.qsf','.qpf']):continue
  if kind=='arm' and (any(x.startswith(('obj-','.dep-')) for x in p.parts) or p.suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or p.name in ['.ARG_VERSION','executed-builder.ps1']):continue
  if kind=='host' and p.suffix not in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:continue
  assert sha(e/n)==h,n
  d=out/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);copied[rel]=h
 def put(p,s):p.write_text(s,encoding='utf-8',newline='\n')
 if kind=='fit':
  p=out/'nes_rom_spi.sv';s=p.read_text();assert s.count("8'h5c")==2;put(p,s.replace("8'h5c","8'h5d"))
  p=out/'nes_run_observer134.sv';put(p,p.read_text().replace("8'hd7","8'hd8"))
  p=out/'rtl/nes.v';s=p.read_text()
  s=once(s,'assign rom_cpu_sample=(cart_ce || cpu_ce) && mr_int && prg_addr[15] && prg_allow;', '''//141 This selected MMC3 adapter never consumes ROM data on cart_ce.
// The last open-bus capture is div11; T65, OAM DMA and DMC consume at cpu_ce.
// Keep both real deadlines. Neither CPU/PPU clocks nor memory read phases move.
// Future adapters with cart_ce ROM-data dependencies must restore that deadline.
assign rom_cpu_sample=((div_cpu == div_cpu_n - 5'd1) || cpu_ce) && mr_int && prg_addr[15] && prg_allow;''')
  put(p,s)
  p=out/'nes_rom_physical.sv';s=p.read_text()
  s=once(s,'data_hold<=lane?psram_data[7:0]:psram_data[15:8];state<=HOLD;', '''data_hold<=lane?psram_data[7:0]:psram_data[15:8];state<=HOLD;
      //141 Launch completion with held data; both cross the unchanged two-stage
      // return synchronizer. Source consumption is >=2 NES edges later, well
      // after the following memory edge releases CE/OE. CHECK remains RELEASE.
      if(!owner_check)ack_toggle<=request_sync[1];''')
  s=once(s,'     if(!owner_check)ack_toggle<=request_sync[1];\n    end\n    RELEASE:', '    end\n    RELEASE:')
  s=s.replace('//140 Data was sampled on the previous memory edge. CE/OE are released\n     // on this edge. Publish RUN completion now; keep RELEASE and IDLE intact.\n     // The source still observes ACK through its original two-stage chain.', '//141 Data/ACK were launched at capture. This following edge releases pins;\n     // keep the full sample HOLD interval, RELEASE and IDLE intact.')
  put(p,s)
  p=out/'nes_rom_service.sv';s=p.read_text()
  s=once(s,'reg cpu_cached,ppu_cached;', 'reg ppu_previous_cached;reg [14:0] ppu_previous_tag;reg [7:0] ppu_previous_byte;\n reg cpu_cached,ppu_cached;')
  s=once(s,'assign ppu_valid=', 'wire ppu_previous_hit=ppu_previous_cached && ppu_previous_tag==ppumem_addr[14:0];\n assign ppu_valid=')
  s=once(s,'(ppu_cached && ppu_tag==ppumem_addr[14:0]) || ppu_reply','(ppu_cached && ppu_tag==ppumem_addr[14:0]) || ppu_previous_hit || ppu_reply')
  s=once(s,'assign ppu_data=ppu_reply?rom_data:ppu_byte;', 'assign ppu_data=ppu_reply?rom_data:((ppu_cached && ppu_tag==ppumem_addr[14:0])?ppu_byte:ppu_previous_byte);')
  s=once(s,'cpu_cached<=0;ppu_cached<=0;', 'ppu_previous_cached<=0;ppu_previous_tag<=0;ppu_previous_byte<=0;\n   cpu_cached<=0;ppu_cached<=0;')
  s=once(s,'if(pending_ppu)begin ppu_cached<=1;', '''//141 Keep the preceding immutable CHR byte across alternating low/high
    // pattern-plane reads. Only validated replies fill either entry; common
    // reset invalidates both. Physical address tags preserve mapper isolation.
    if(pending_ppu)begin
     ppu_previous_cached<=ppu_cached;ppu_previous_tag<=ppu_tag;ppu_previous_byte<=ppu_byte;
     ppu_cached<=1;''')
  s=once(s,'reg cpu_cached,ppu_cached;', 'reg [7:0] cpu_line_valid;reg [12:0] cpu_line_tag[0:7];reg [7:0] cpu_line_byte[0:7];integer cache_index141;\n reg cpu_cached,ppu_cached;')
  s=once(s,'((cpu_cached && cpu_tag==cpumem_addr[15:0]) || cpu_reply)', '((cpu_line_valid[cpumem_addr[2:0]] && cpu_line_tag[cpumem_addr[2:0]]==cpumem_addr[15:3]) || cpu_reply)')
  s=once(s,'assign cpu_data=cpu_reply?rom_data:cpu_byte;', 'assign cpu_data=cpu_reply?rom_data:cpu_line_byte[cpumem_addr[2:0]];')
  s=once(s,'busy<=0;pending_ppu<=0;pending_address<=0;age<=0;', '''busy<=0;pending_ppu<=0;pending_address<=0;age<=0;
   cpu_line_valid<=0;
   for(cache_index141=0;cache_index141<8;cache_index141=cache_index141+1)begin cpu_line_tag[cache_index141]<=0;cpu_line_byte[cache_index141]<=0;end''')
  s=once(s,'else begin cpu_cached<=1;', '''//141 Eight direct-mapped immutable PRG bytes relieve repeated instruction
    // fetches. Full physical tags, validated replies, common-reset invalidation.
    else begin
     cpu_line_valid[pending_address[2:0]]<=1;cpu_line_tag[pending_address[2:0]]<=pending_address[15:3];cpu_line_byte[pending_address[2:0]]<=rom_data;
     cpu_cached<=1;''')
  put(p,s)
 else:
  root=out/'src' if kind=='arm' else out
  versions=['nes_menu_diagnostic.c','nes_checkpoint112.c','nes_h1_stm32.c','nes_run136.inc','nes_cf86_session094.c','nes_cf86_session094.h']
  ids=['nes_h1_stm32.c','nes_rom_verify.c','nes_run136.inc']
  models=['card.c','config097_card.inc','host109.c','platform.c'] if kind=='host' else []
  for name in set(versions+ids+models):
   p=root/name;s=p.read_text(encoding='utf-8')
   pieces=re.split(r'(\b0x[0-9a-fA-F]+)',s)
   t=''.join(x if i%2 else x.replace('140','141') for i,x in enumerate(pieces))
   assert re.findall(r'\b0x[0-9a-fA-F]+',s)==re.findall(r'\b0x[0-9a-fA-F]+',t),name
   if name in ids+models:t=re.sub(r'\b0x5c\b','0x5d',t);t=re.sub(r'\b0xd7\b','0xd8',t)
   if name=='platform.c':t=re.sub(r'\b0x5b\b','0x5c',t);t=re.sub(r'\b0xd6\b','0xd7',t)
   t=t.replace('board_expected_hex=5c','board_expected_hex=5d')
   if t!=s:put(p,t)
  p=root/'nes_menu_return.c';s=p.read_text()
  s=once(s,'static struct nes_diag_wait io_wait;', '''static struct nes_diag_wait io_wait;
/*141 The final report has its own budget, like progress checkpoints. Returning
 * from logging restores the caller's remaining polls AND original start time. */
static bool log_saved_active141;
static struct nes_diag_wait log_saved_wait141;''')
  s=once(s,'void nes_return_log_allow(bool allow){log_allowed=allow;if(allow){io_active=true;io_wait=nes_diag_wait_start(1000,10000u);}}', '''void nes_return_log_allow(bool allow){
 if(allow){
  if(log_allowed||checkpoint_window112){nes_return_fail(NES_DIAG_MENU);return;}
  log_saved_active141=io_active;log_saved_wait141=io_wait;
  log_allowed=true;io_active=true;io_wait=nes_diag_wait_start(1000,10000u);
 }else if(log_allowed){
  log_allowed=false;io_active=log_saved_active141;io_wait=log_saved_wait141;
 }
}''');put(p,s)
  if kind=='arm':put(root/'VERSION','RELEASE_VERSION = "NES-SCREEN141"\n')
  if kind=='host':
   p=root/'config097_card.inc';put(p,p.read_text().replace('nes_return_log_allow(true);','nes_return_log_allow(false);nes_return_log_allow(true);'))
   # The extracted main remains byte-identical; stress cost is injected by a
   # wrapper at its existing prepared() seam, never in the product main.
   p=root/'host109.c';s=p.read_text();needle='#include "main098.inc"'
   assert needle in s
   s=s.replace(needle,'''static bool prepared_budget141(bool ok){
 bool result=nes_menu_diagnostic_prepared(ok);
 if(result&&run_case136==20){for(unsigned i=0;i<20000;i++)assert(nes_return_io_step());}
 return result;
}
#define nes_menu_diagnostic_prepared prepared_budget141
#include "main098.inc"
#undef nes_menu_diagnostic_prepared''')
   s=s.replace('if(run_case136==0)assert(nes_run136.passed', 'if(run_case136==0||run_case136==20)assert(nes_run136.passed')
   put(p,s)
   #20 is a normal RUN with extra post-report work, not a synthetic ROM fault.
   p=root/'platform.c';s=p.read_text();s=s.replace('(run_case136==3||run_case136>=16)','(run_case136==3||(run_case136>=16&&run_case136<=19))');put(p,s)
 put(out/'preparation141.json',json.dumps(dict(copied=copied,changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h}),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--kind',choices=['fit','arm','host'],required=True)
 a=p.parse_args();prepare(a.baseline,a.out,a.kind)
