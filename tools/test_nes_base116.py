# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,subprocess,re
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
from nes_base116 import adapt

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence113','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--cases',default='71,72,73,74,75,76,77,70')
 a=p.parse_args();o=a.out.resolve();e=a.evidence113.resolve();assert not o.exists();o.mkdir(parents=True)
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/entry113-verification.json').read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 for f in (e/'host02').rglob('*'):
  if f.is_file() and f.suffix in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:
   assert sha(f)==pins[f.relative_to(e).as_posix()]
   d=o/f.relative_to(e/'host02');d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,d)
 adapt(o)
 def edit(n,old,new):
  f=o/n;f.write_text(once(f.read_text(encoding='utf-8'),old,new),encoding='utf-8',newline='\n')
 edit('host109.c','entry_card113(entry_case113);','''entry_card113(entry_case113);
 if(entry_case113==72)scenario096=1008;
 if(entry_case113==73)scenario096=1009;
 if(entry_case113==74)scenario096=1074;
 if(entry_case113==75)fault=BASE_TOKEN;
 if(entry_case113==76)card_phase_fault096(5,2,1);
 if(entry_case113==77)css_case109=3;''')
 edit('host109.c','"NES ENTRY 113.nh1"','"NES BASE 116.nh1"')
 h=o/'host109.c';t=h.read_text(encoding='utf-8');begin=t.index(' if(!run112){');end=t.index(' /* main begins only after base restoration;',begin)
 t=t[:begin]+''' if(!run112){
  assert(entry_case113>=72&&entry_case113<=76);
  assert(nes_return_failed()&&!irq&&reset_held&&!release097&&!finishes&&!check_acks&&!count);
  unsigned c=card_commands096(),edges=card_edges096(),fr=frames;
  if(entry_case113==76)assert(first_error096&&c==first_commands096&&edges==first_edges096&&fr==first_frames096);
  assert(!nes_checkpoint112("FORBIDDEN",0,0));
  assert(c==card_commands096()&&edges==card_edges096()&&fr==frames);
  printf("PASS116 rejected case=%u commands=%u configs=%u error=%u\\n",entry_case113,c,configs,nes_diag_status()->error);return 0;
 }
 assert(configs==2&&!irq&&reset_held&&stop_count==1);
 if(entry_case113==70)assert(finishes==1&&check_acks==original_length-16);
 else assert(!finishes&&!check_acks&&!check_reads&&!end_count&&!count);
 scenario098=0;
'''+t[end:];h.write_text(t,encoding='utf-8',newline='\n')
 # Actual production SPI registers; inject only the environment response.
 edit('host098-prefix.inc','if(scenario096==1009&&configs==2)mock_spi.SR=SPI_SR_BSY;', 'if(scenario096==1009&&configs==2)mock_spi.SR=SPI_SR_BSY;\n if(scenario096==1074&&configs==2)mock_spi.SR=0;')
 f=o/'card.c';t=f.read_text(encoding='utf-8').replace('NES113 seq=','NES116 seq=').replace('nes-progress-113.txt','nes-progress-116.txt');f.write_text(t,encoding='utf-8',newline='\n')
 sources=['card.c','host109.c','printf103.c','linked109-css.c','linked112-checkpoint.c']+['linked103-'+n.replace('/','-') for n in ['ff.c','unicode/ccsbcs.c','nes_diag_runtime.c','nes_menu_return.c','nes_menu076.c','nes_cf86_session094.c','nes_h1_stm32.c','nes_h1_session.c','nes_rom_spi.c','nes_rom_verify.c','nes_menu_diagnostic.c']]
 cmd=[str(a.gcc),'-std=c11','-O2','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-Wno-format','-D__USE_MINGW_ANSI_STDIO=1','-fno-builtin','-ffunction-sections','-fdata-sections','-I.','-DGBC_SAVE_G12','-DGBC_DUMP_G12',*sources,'-Wl,--gc-sections','-o','host.exe']
 with (o/'compile.log').open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT)
 assert not r.returncode,(o/'compile.log').read_text(errors='replace')[-5000:]
 results=[]
 for case in map(int,a.cases.split(',')):
  log=o/f'case-{case}.log'
  with log.open('wb') as f:r=subprocess.run([str(o/'host.exe'),str(case),'0',*[str(o/n) for n in ['fixture.nes','diag.packed','diag.raw','base.packed','base.raw','menu.bin']]],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  t=log.read_text(errors='replace');assert not r.returncode and ('PASS116' in t or 'PASS109' in t),(case,r.returncode,t[-3500:])
  records=(o/'checkpoint-sectors.txt').read_bytes();(o/f'case-{case}-records.txt').write_bytes(records)
  stages=re.findall(rb'stage=([A-Z_]+)',records)
  if case in [70,71]:
   for st in [b'BASE_FILE_OPEN_NEXT',b'BASE_FILE_OPENED',b'BASE_PINS_READY',b'BASE_STREAM_END',b'BASE_DONE_HIGH',b'BASE_PGM_OK',b'BASE_SPI_STATE_NEXT',b'BASE_TOKEN_NEXT',b'BASE_TOKEN_RESULT',b'BASE_DONE',b'MENU_PREPARED']:assert st in stages,st
   logical=(o/'entry-logical.txt').read_bytes();assert b'MENU_PREPARED' in logical;(o/f'case-{case}-logical.txt').write_bytes(logical)
   if case==71:assert b'BEGIN_LOAD' not in stages and b'CHECK' not in stages and b'OPEN_INPUT' not in stages and b'EMPTY_STOP_NEXT' in stages
  else:
   assert b'BASE_DONE' not in stages and b'MENU_PREPARED' not in stages
   if case==72:assert b'BASE_DONE_TIMEOUT' in stages
   if case in [73,74]:assert b'BASE_SPI_STATE_NEXT' in stages and b'BASE_TOKEN_NEXT' not in stages
   if case==75:assert b'BASE_TOKEN_RESULT' in stages
  results.append(dict(case=case,log_sha256=sha(log),records=len(stages)))
 (o/'result.json').write_text(json.dumps(dict(cases=results,physical=False),indent=2)+'\n',encoding='utf-8')
 shutil.copy2(__file__,o/'executed-test116.py');print('PASS116',len(results),'cases')
if __name__=='__main__':main()
