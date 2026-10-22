# SPDX-License-Identifier: MIT
"""Re-execute actual2472 C planner, recording sorted encoded ROM tile plans.

Saved successful ACKs drive this deterministic host replay. Every request and
converted bank must equal the original run; no CPU or timing claim is made.
"""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_delta231 import BASE,ROOT,sha,once
from measure_nes_dma247 import short
from run_nes_scroll229 import ROM_SHA

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);a=p.parse_args();d=a.out.resolve()
 assert not d.exists() and d.as_posix().isascii() and sha(a.rom)==ROM_SHA;d.mkdir(parents=True)
 old=BASE/'probes/nes-wholepath247/jointdecode-host01';ref=BASE/'probes/nes-wholepath247/jointdecode-test02/run';pins={}
 for path in old.iterdir():
  if path.suffix in ('.c','.h','.inc'):shutil.copyfile(path,d/path.name);pins[path.relative_to(BASE).as_posix()]=sha(path)
 s=(d/'host.c').read_text(encoding='utf-8')
 s=once(s,'static bool order_flush247(void){','''static bool order_flush247(void){
 if(order_count247){char name[80];sprintf(name,"plans%u.bin",fixture247[0].gen);FILE *pf=fopen(name,"ab");assert(pf);
  uint8_t h[3]={(uint8_t)order_bytes247,(uint8_t)(order_bytes247>>8),(uint8_t)order_count247};
  assert(fwrite(h,1,3,pf)==3&&fwrite(order_buffer247,1,order_bytes247,pf)==order_bytes247);fclose(pf);}
''')
 (d/'host.c').write_text(s,encoding='utf-8',newline='\n')
 for path in ref.glob('ack-*.bin'):shutil.copyfile(path,d/path.name);pins[path.relative_to(BASE).as_posix()]=sha(path)
 palette=BASE/'probes/nes-delta231/test07/palette.bin';shutil.copyfile(palette,d/'palette.bin');pins[palette.relative_to(BASE).as_posix()]=sha(palette)
 gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
 files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
 for name,cmd in [('build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror',*files,'-o','host.exe']),('run',[str(d/'host.exe'),short(BASE/'probes/nes-geometry230/rtl02'),short(a.rom.resolve()),'905','975',short(BASE/'probes/nes-delta231/test07')])]:
  with (d/(name+'.log')).open('wb') as log:r=subprocess.run(cmd,cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-2500:]
 rows=[]
 for f in sorted(ref.glob('req-*.bin')):assert (d/f.name).read_bytes()==f.read_bytes();pins[f.relative_to(BASE).as_posix()]=sha(f)
 for g in range(1,72):
  f=ref/f'bank-{g}.bin';assert (d/f.name).read_bytes()==f.read_bytes();pins[f.relative_to(BASE).as_posix()]=sha(f)
  raw=(d/f'plans{g}.bin').read_bytes();at=0;nplans=0;batches=0;payload=0
  while at<len(raw):
   n=int.from_bytes(raw[at:at+2],'little');count=raw[at+2];at+=3;assert 1<=count<=15 and 3<=n<=240 and at+n<=len(raw)
   at+=n;payload+=n;nplans+=count;batches+=1
  rows.append(dict(frame=g+904,plans=nplans,batches=batches,payload=payload,minimum_E9_bytes=payload+8*batches+11)) # separate END3B+8B frame
 # Private game bytes only; never copy this output tree into Git.
 (d/'chr.hex').write_text(a.rom.read_bytes()[16+262144:16+262144+131072].hex(' ')+'\n')
 r=dict(passed=True,scope=__doc__,frames=rows,ROM_sha256=ROM_SHA,input_hashes=pins,script_sha256=sha(Path(__file__)))
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(dict(passed=True,frames=len(rows),plans=sum(x['plans'] for x in rows),max_E9_bytes=max(x['minimum_E9_bytes'] for x in rows[2:]))))

if __name__=='__main__':main()
