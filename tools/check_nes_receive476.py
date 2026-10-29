# SPDX-License-Identifier: MIT
"""Compare actual old/new C bitmap and CRC boundaries, and linked M4 fault paths."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from profile_nes_receive476 import profile, sha

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base',type=Path,required=True)
parser.add_argument('--arm',type=Path,required=True)
parser.add_argument('--rpc',type=Path,required=True)
parser.add_argument('--gcc',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
for header in args.base.glob('*.h'):shutil.copyfile(header,out/header.name)
shutil.copyfile(args.base/'nes_trace166.c',out/'nes_trace166.c')
shutil.copyfile(ROOT/'tests/nes-receive476/check.c',out/'check.c')
for label,source in [('base',args.base),('candidate',args.arm)]:
 shutil.copyfile(source/'nes_native165.c',out/(label+'_native.c'))
 macros='\n'.join('#define nes_native165_'+name+' '+label+'_'+name for name in ['reset','packet','poll','prepare','consumed'])
 wrapper=macros+'\n#define nes_native181_pixels '+label+'_pixels\n#include "'+label+'_native.c"\n'
 wrapper+='uint16_t crc476_'+label+'(const uint8_t *p,unsigned n){return crc16(p,n);}\n'
 (out/(label+'.c')).write_text(wrapper,encoding='utf8',newline='\n')
for name,cmd in [('build',[str(args.gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','check.c','base.c','candidate.c','nes_trace166.c','-o','check.exe']),('native',[str(out/'check.exe')])]:
 with (out/(name+'.log')).open('wb') as log:run=subprocess.run(cmd,cwd=out,stdout=log,stderr=subprocess.STDOUT)
 assert run.returncode==0,(out/(name+'.log')).read_text(errors='replace')
result={'passed':True,'native':(out/'native.log').read_text().strip(),'M4':{}}
for fault in [None,'status_crc','read_crc','read_payload','read_transfer','geometry_with_valid_crc','pop_crc','retire_token','prepare_transfer']:
 old=profile(args.base,args.rpc,fault);new=profile(args.arm,args.rpc,fault)
 assert old['full_state_sha256']==new['full_state_sha256'] and old['source_transactions']==new['source_transactions'],fault
 result['M4'][fault or 'normal']={'base':old,'candidate':new}
 print('PASS',fault or 'normal',flush=True)
result['inputs']={'base_C':sha(args.base/'nes_native165.c'),'candidate_C':sha(args.arm/'nes_native165.c'),'test_C':sha(ROOT/'tests/nes-receive476/check.c')}
result['limits']='Native synthetic bitmap/CRC cases plus linked M4 replay; not full RUN/IRQ/physical stack/FPS or a new STOP/finalACK hardware measurement.'
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(result['native'])
