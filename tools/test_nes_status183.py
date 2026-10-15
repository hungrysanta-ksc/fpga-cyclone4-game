# SPDX-License-Identifier: MIT
"""Replay actual frozen1813 SPI bytes; skip only an identical positive D0."""
from pathlib import Path
import argparse,json,shutil,subprocess,os
from nes_game147 import ROOT,sha
from nes_clip178 import replace
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 frozen=ROOT.parent/'probes/nes-packed181/evidence/test02';meta=json_read(frozen/'result.json')
 for n in ['nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h']:shutil.copyfile(a.arm/'src'/n,a.out/n)
 host=(ROOT/'tests/nes-functional/packed181_host.c').read_text()
 host=replace(host,'unsigned mode,calls;bool injected,confirm;','unsigned mode,calls;bool injected,confirm;unsigned skipped,last;uint8_t previous[8];')
 host=replace(host,'assert(fscanf(r->f,"%u %518s %518s",&count,a,b)==3&&count==n&&strlen(a)==n*2&&strlen(b)==n*2);r->calls++;', '''assert(fscanf(r->f,"%u %518s %518s",&count,a,b)==3);
 if(tx[0]==0xd1 && hex(a)==0xd0){
  assert(r->last==0xd0 && count==8 && (r->previous[2]&1));
  for(unsigned i=0;i<8;i++)assert(hex(b+i*2)==r->previous[i]);
  r->skipped++;assert(fscanf(r->f,"%u %518s %518s",&count,a,b)==3);
 }
 assert(count==n&&strlen(a)==n*2&&strlen(b)==n*2);r->calls++;''')
 host=replace(host,' if(!r->injected&&tx[0]==0xd1', ' r->last=tx[0];if(n==8)memcpy(r->previous,rx,8);\n if(!r->injected&&tx[0]==0xd1')
 host=replace(host,'tx[0]==0xd1&&(r->mode==1||r->mode==2)','tx[0]==0xd1&&r->skipped&&(r->mode==1||r->mode==2)')
 host=replace(host,'struct replay r={fopen(argv[1],"r"),mode,0,false,false};','struct replay r={.f=fopen(argv[1],"r"),.mode=mode};')
 host=replace(host,'copy.next_token=0;copy.token_valid=false;','copy.next_token=0;copy.token_valid=false;memset(copy.status183,0,8);copy.ready183=false;printf("REPLAY calls=%u skipped=%u prefix=%u\\n",r.calls,r.skipped,(unsigned)offsetof(struct nes_native165,status183));')
 host=replace(host,' negatives();printf(', ''' /* Invalid cached CRC fails before any SPI; reset must discard cache. */
 reset();S.ready183=true;memset(S.status183,0,8);
 assert(!nes_native165_poll(&S,NULL,NULL)&&S.error==0);
 reset();assert(!S.ready183);
 negatives();printf(''')
 # NULL transfer exits argument validation. A separate cache-corruption replay
 # below checks a real callback context, without fabricating a valid packet.
 host=replace(host,'for(unsigned mode=0;mode<5;mode++)','for(unsigned mode=0;mode<7;mode++)')
 host=replace(host,'   ok=nes_native165_poll(&S,transfer,&r);','''   if(mode==5 && S.ready183 && !r.injected){S.status183[7]^=1;r.injected=true;}
   if(mode==6 && S.ready183 && !r.injected){
    S.status183[4]^=1;unsigned c=0;
    for(unsigned i=1;i<7;i++){c^=S.status183[i];for(unsigned j=0;j<8;j++)c=((c<<1)^((c&128)?7:0))&255;}
    S.status183[7]=(uint8_t)c;r.injected=true;
   }
   unsigned before=r.calls;ok=nes_native165_poll(&S,transfer,&r);
   if(mode==5 && r.injected)assert(!ok&&r.calls==before&&S.error==21);
   if(mode==6 && r.injected)assert(!ok&&r.calls==before+1&&S.error==18);''')
 (a.out/'host.c').write_text(host,encoding='utf-8',newline='\n')
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,d,label):
  with (d/(label+'.log')).open('wb') as f:q=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  assert q.returncode==0,(d/(label+'.log')).read_text(errors='replace')
 run([a.gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','host.c','nes_native165.c','nes_trace166.c','-o','host.exe'],a.out,'gcc')
 cases=[]
 for name,patches in [('patch0',0),('patch1',1),('patch7',7),('maxgroups',7)]:
  old=frozen/name;d=a.out/name;d.mkdir()
  for n in ['transactions.txt','records.hex']:shutil.copyfile(old/n,d/n)
  run([a.out/'host.exe',d/'transactions.txt',d/'records.hex',patches],d,'host')
  new=(d/'receiver.bin').read_bytes();ref=(old/'receiver.bin').read_bytes()
  import re
  log=(d/'host.log').read_text();m=re.search(r'REPLAY calls=(\d+) skipped=(\d+) prefix=(\d+)',log);assert m
  prefix=int(m[3]);assert new[:prefix]==ref[:prefix]
  assert int(m[2])>0
  cases.append(dict(name=name,log=log.strip(),calls=int(m[1]),skipped=int(m[2]),logical_prefix_bytes=prefix,inputs={n:sha(old/n) for n in ['transactions.txt','records.hex']},equal=True))
 result=dict(passed=True,cases=cases,source_pins={n:sha(a.out/n) for n in ['nes_native165.c','nes_native165.h','nes_trace166.c','nes_trace166.h']},public_sources={n:sha(ROOT/n) for n in ['tools/nes_status183.py','tools/test_nes_status183.py','tests/nes-functional/packed181_host.c']},scope='Actual frozen RTL SPI bytes replay, identical positive D0 elision only; not new RTL timing or physicalFPS.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
def json_read(p):return json.loads(p.read_bytes())
if __name__=='__main__':main()
