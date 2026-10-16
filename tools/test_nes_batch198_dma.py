# SPDX-License-Identifier: MIT
"""Check198 in-place transfers with unchanged deployed186 DMA C/register model."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]; BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True);a=p.parse_args()
 a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 source=BASE/'probes/nes-paired186/arm01/src'
 pins={}
 for name in ('nes_native165_bulk.inc','nes_dma182.inc','nes_rom_spi.h'):
  f=source/name;shutil.copy2(f,a.out/name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 f=ROOT/'tests/nes-functional/dma182_host.c';s=f.read_text();pins[f.relative_to(BASE).as_posix()]=sha(f)
 for old,new in [('rx_data[1+rx_at]=sent[rx_at]^0x96u','tx_data[1+rx_at]=sent[rx_at]^0x96u'),('streams[0].M0AR==0x3000','streams[0].M0AR==0x2000'),('tx_data+1,rx_data+1,count','tx_data+1,tx_data+1,count'),('int main(void)','int legacy_main(void)')]:
  assert s.count(old)==1,old;s=s.replace(old,new)
 s+='''
int main(void){
 unsigned success=0,errors=0;
 for(unsigned n=1;n<=248;n++)for(unsigned speed=1;speed<=17;speed+=8){
  reset(n,speed);assert(run());stopped();
  assert(tx_at==n&&rx_at==n&&early_tx_done==1&&wait_calls==4);
  assert(tx_data[0]==0&&tx_data[n+1]==(uint8_t)((n+1)*73u));
  for(unsigned i=0;i<n;i++){
   assert(sent[i]==(uint8_t)((i+1)*73u));
   assert(tx_data[i+1]==(uint8_t)(((i+1)*73u)^0x96u));
  }
  success++;
 }
 for(unsigned i=1;i<=248;i++){
  reset(248,9);fault_byte=i;dma_fault=DMA_LISR_TEIF0;
  assert(!run()&&failed&&tx_at==i);stopped();
  unsigned before=tx_at;assert(!run()&&tx_at==before);
  assert(tx_data[0]==0&&tx_data[249]==(uint8_t)(249*73u));errors++;
 }
 printf("PASS DMA198 inplace_success=%u byte_faults=%u maxbytes=248\\n",success,errors);
 return 0;
}
'''
 (a.out/'host.c').write_text(s,encoding='utf8',newline='\n')
 for tag,cmd in [('build',[a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','host.c','-o','host.exe']),('host',[a.out/'host.exe'])]:
  with (a.out/(tag+'.log')).open('wb') as log:r=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=60)
  assert r.returncode==0,(tag,r.returncode,(a.out/(tag+'.log')).read_text(errors='replace'))
 result=dict(passed=True,success=744,byte_faults=248,host=(a.out/'host.log').read_text().strip(),source_pins=pins,script_sha256=sha(Path(__file__)),scope='Unchanged deployed186 driver + asynchronous register model, TX==RX. Not STM32 bus/arbitration/WCET or full ARM approval.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
