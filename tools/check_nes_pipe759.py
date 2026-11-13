# SPDX-License-Identifier: MIT
"""Execute the materialized DMA owner with asynchronous peripheral/fault stimuli."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from nes_raw506 import once,sha

def verify(src,gcc,out):
    out.mkdir(exist_ok=False)
    for n in ('nes_native165_bulk.inc','nes_dma182.inc','nes_rom_spi.h','nes_cost471.h'):
        shutil.copyfile(src/n,out/n)
    harness=Path('tests/nes-functional/dma182_host.c').read_text()
    harness=once(harness,'int main(void){', '''uint32_t nes_cost471_now(void){return 0;}
void nes_cost471_op(unsigned op,unsigned n,uint32_t t){(void)op;(void)n;(void)t;}
static unsigned calls,trip;
bool nes_map759_step(void){
 assert(selected && !failed && spi.CR2==(SPI_CR2_RXDMAEN|SPI_CR2_TXDMAEN));
 calls++;if(calls==trip)failed=true;
 return true;
}
int main(void){
 reset(211,9);tx_data[1]=0xe1;tx_data[2]=2;tx_data[3]=2;
 assert(run() && calls>1);stopped();unsigned successful=calls;
 for(unsigned i=1;i<=successful;i++){
  reset(211,9);tx_data[1]=0xe1;tx_data[2]=2;tx_data[3]=2;calls=0;trip=i;
  assert(!run() && calls==trip);stopped();
 }
 printf("MAP DMA planner guard positions=%u\\n",successful);
 calls=trip=0;''')
    (out/'guard.c').write_text(harness,newline='\n')
    env=dict(os.environ,PATH=str(gcc.resolve().parent)+os.pathsep+os.environ['PATH'])
    subprocess.run([str(gcc),'-std=c11','-O2','-Wall','-Wextra','-Werror','guard.c','-o','guard.exe'],cwd=out,env=env,check=True)
    log=subprocess.check_output([str((out/'guard.exe').resolve())],cwd=out,env=env,text=True)
    (out/'result.json').write_text(json.dumps(dict(log=log,bulk=sha(src/'nes_native165_bulk.inc'),
      wait=sha(src/'nes_dma182.inc'),firmware=sha(src/'obj-nes-100/firmware.stm')),indent=2)+'\n')
    print(log)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('src','gcc','out'):p.add_argument(k,type=Path)
    a=p.parse_args();verify(a.src,a.gcc,a.out)
