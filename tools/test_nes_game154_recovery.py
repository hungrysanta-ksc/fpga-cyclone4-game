# SPDX-License-Identifier: MIT
"""Actual154 MCU with valid/malformed auxiliary SPI state through menu return."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_game147 import ROOT,ROM_SHA,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','arm','rom','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;e=a.baseline/'nes-game153/evidence';s=a.arm/'src'
 assert not o.exists() and str(o).isascii() and sha(a.rom)==ROM_SHA
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game153-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];o.mkdir(parents=True)
 for n,h in pins.items():
  if not n.startswith('host/') or Path(n).suffix not in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:continue
  src=e/n;assert sha(src)==h;dst=o/n[5:];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 # Reuse153 actual-source list and unchanged transport adapter exactly.
 exact=list(json.loads((e/'host/result.json').read_bytes())['actual_sources'])
 for n in exact:shutil.copy2(s/n,o/n)
 shutil.copy2(s/'ccsbcs.c',o/'unicode/ccsbcs.c')
 def edit(n,old,new):
  q=o/n;t=q.read_text();assert old in t,(n,old);q.write_text(t.replace(old,new),encoding='utf8',newline='\n')
 for n in ['host109.c','card.c','config097_card.inc']:
  t=(o/n).read_text();(o/n).write_text(t.replace('153','154'),encoding='utf8',newline='\n')
 edit('platform.c','0xdc','0xdd');edit('platform.c','fault==SPI_ID?0:0x62','fault==SPI_ID?0:0x63')
 edit('platform.c',"if(tx[0]==0x71||tx[0]==0x72||tx[0]==0x73)","if(tx[0]>=0x71&&tx[0]<=0x75)")
 edit('platform.c',"if(tx[0]==0x73){",'''if(tx[0]==0x74||tx[0]==0x75){
     assert(reset_held&&stop_count); /* new reads must occur AFTER safe STOP */
     const uint64_t ctx=0x60b6a800484043feull; /* synthetic, not physical evidence */
     reply[1]=AUX_BAD?0xdc:0xdd;reply[2]=1;
     if(tx[0]==0x74)for(unsigned i=0;i<5;i++)reply[3+i]=(uint8_t)(ctx>>(56-8*i));
     else{reply[3]=ctx>>16;reply[4]=ctx>>8;reply[5]=ctx;reply[6]=2;reply[7]=1;}
    }else if(tx[0]==0x73){''')
 sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']
 sources += ['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 result={}
 for bad in [0,1]:
  label='bad-aux' if bad else 'valid-aux';exe=o/(label+'.exe')
  cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12','-DOLD154=0','-DAUX_BAD='+str(bad),*sources,'-Wl,--gc-sections','-o',str(exe)]
  for stage,command in [('build',cmd),('run',[str(exe),'3','0',str(a.rom.resolve()),*[str(o/n) for n in ['diag.packed','diag.raw','base.packed','base.raw','menu.bin']]])]:
   r=subprocess.run(command,cwd=o,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240);(o/(label+'-'+stage+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')[-3500:]
  assert b'PASS109' in r.stdout and b'release=1 blocked=0' in r.stdout
  report=(o/'saved-report146.txt').read_text();progress=(o/'checkpoint-sectors.txt').read_text()
  for line in ['candidate=NES-GAME-154','run_rom_error=2','fault_context_hi=e200c2f4','fault_context_lo=30217a19','stop_ok=1','base_restored=1','safe_to_reload=1','ppu_state_valid='+str(1-bad), 'ppu_state_hi='+('00000000' if bad else '60b6a800'),'ppu_state_lo='+('00000000' if bad else '484043fe')]:assert line+'\n' in report,line
  assert all(n in progress for n in ['DISPLAY_STOPPED','BASE_DONE','MENU_PREPARED'])
  (o/(label+'-report.txt')).write_text(report);(o/(label+'-progress.txt')).write_text(progress)
  result[label]=dict(passed=True,auxiliary_valid=not bad)
 for n in exact:assert sha(o/n)==sha(s/n),n
 result.update(passed=True,actual_sources={n:sha(s/n) for n in exact},physical=False,scope='Actual MCU/FatFS/menu with modeled SD/GPIO/SPI peer. New PPU state read after STOP; malformed auxiliary ID leaves validity0 and preserves recovery. Not transport clock failure or actual fault cause proof.')
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
