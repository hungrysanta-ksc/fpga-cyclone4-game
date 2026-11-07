"""Replace overlapping 64-byte repeat probes with one forward scan on MMC666."""
import argparse
import shutil
from pathlib import Path
from check_nes_fault641 import digest, evidence
from nes_raw506 import once


def prepare(base, out, mode='linear'):
    assert digest(base/'src/obj-nes-100/firmware.stm') == evidence('trial666-package.json')['firmware_SHA256']
    shutil.copytree(base, out, ignore=shutil.ignore_patterns('obj-*', '.dep-*', '*.log', '*.json'))
    p = out/'src/nes_native_sink165.c'
    old = ''' for(unsigned i=1;i<end&&i+64<=n;i++)if(repeat_bytes(b+i,64)==64)return i;'''
    new = ''' /* A mismatch at j excludes every start through j-2: those spans
  * contain unequal bytes two positions apart. Resume at j-1, retaining
  * the earliest possible 64-byte run and the original packet boundaries.
  * No data changes or history/credit decisions occur in this scan. */
 for(unsigned i=1;i<end&&i+64<=n;){
  unsigned j=i+2;
  while(j<i+64&&b[j]==b[j-2])j++;
  if(j==i+64)return i;
  i=j-1;
 }'''
    s=once(p.read_text(), old, new)
    if mode=='drain':
        s=once(s, 'if(s->plan && s->plan->window && (((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu){',
               '''/* Finish consumption of a nonempty accepted map batch before
  * publishing the nonmap tail. This is a checked credit boundary, not a
  * DMA/display completion claim or a fixed timing delay. STOP still wins. */
 if(s->plan && s->plan->window && r->map_upload){''')
        s=once(s, 'if(s->displayed && s->obj_next>=16 && s->plan->window->wait){',
               'if((((uint32_t)(r->map_upload>>32))&0x7ffffu)==0x7ffffu && s->displayed && s->obj_next>=16 && s->plan->window->wait){')
    p.write_text(s, newline='\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--mode',choices=('linear','drain'),default='linear')
    a=p.parse_args();prepare(a.base,a.out,a.mode)
