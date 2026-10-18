# SPDX-License-Identifier: MIT
"""Host-only replay of existing193 chunk rules; no RTL timing/token proof."""
import inspect
import prepare_nes_batchorder247 as prior
from nes_delta231 import once

COALESCE=r'''
/* Models193 OPEN/CHECK/SEAL payload grouping, not CDC or buffer scheduling.
 * Preserve an open chunk across encoded plan batches, until mismatch/END. */
static uint8_t chunk247[2048];static unsigned used247,kind247,slot247,gen247;
static FILE *chunks247;
static bool chunk_flush247(void){
 if(!used247)return true;
 fprintf(chunks247,"%u,%u,%u,%u\n",gen247,kind247,slot247,used247);fflush(chunks247);
 if(!bulk232(kind247,slot247,gen247,chunk247,used247))return false;
 used247=0;return true;
}
static bool chunk_queue247(unsigned kind,unsigned slot,unsigned gen,const uint8_t *bytes,unsigned n){
 unsigned unit=kind?32:16;assert(kind<2&&n==unit&&slot<(kind?128u:1024u));
 if(used247){
  assert(gen==gen247);
  if(kind!=kind247||slot!=slot247+used247/unit||used247+n>2048)
   if(!chunk_flush247())return false;
 }
 if(!used247){kind247=kind;slot247=slot;gen247=gen;}
 memcpy(chunk247+used247,bytes,n);used247+=n;return true;
}
'''


def main():
    s=inspect.getsource(prior.main)
    queue=COALESCE+once(prior.QUEUE,'if(!bulk232(fixture247[j].kind,','if(!chunk_queue247(fixture247[j].kind,')
    at="    f.write_text(s,encoding='utf-8',newline='\\n')"
    addition='''    s=once(s,'unsigned at=slot*n;','unsigned at=slot*(kind?32u:16u);')
    s=once(s,'assert(order_flush247());','assert(order_flush247()&&chunk_flush247());')
    s=once(s,' order_log247=fopen(', ' chunks247=fopen("chunks247.csv","w");assert(chunks247);fprintf(chunks247,"generation,kind,slot,bytes\\\\n");\\n order_log247=fopen(')
'''
    s=once(s,at,addition+at)
    s=once(s,"host_only_fixture_bytes='15 converted tiles;not ARM allocation'","host_only_fixture_bytes='15 converted tiles plus2048B chunk;not ARM allocation'")
    s=once(s,"print('PASS: private bounded-batch C replay compiled; not full ARM runtime.')","print('PASS: existing193 grouping fixture compiled;not actual FPGA/ARM runtime.')")
    ns=dict(prior.__dict__);ns.update(QUEUE=queue,__file__=__file__,__doc__=__doc__)
    exec(compile(s,'coalesce247-host','exec'),ns);ns['main']()


if __name__=='__main__':main()
