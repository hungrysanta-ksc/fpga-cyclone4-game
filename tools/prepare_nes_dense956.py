"""Build a diagnostic that retains two dense OBJ traces in the existing menu buffer."""
import shutil
from pathlib import Path
from package_nes_trial704 import read, sha
from prepare_nes_trial802 import rename_edition

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent/'probes/nes-trial955'
WORK = PARENT.with_name('nes-trial956')
SOURCE = WORK/'link/src'


def prepare():
    assert sha(PARENT/'link/src/obj-nes-100/firmware.stm') == read(ROOT/'analysis/trial955-package.json')['firmware']
    shutil.copytree(PARENT/'link', WORK/'link')
    rename_edition(SOURCE, WORK/'markers', 955, 956)
    for marker in (WORK/'markers').iterdir():
        shutil.copyfile(marker, SOURCE/marker.name)
    patch_budget()


def patch_budget():
    s = (PARENT/'link/src/nes_budget210.c').read_text()
    start, end = s.index(' unsigned score='), s.index('    for(unsigned group=0;')
    s = s[:start] + ''' uint32_t desc; memcpy(&desc,r->descriptor+2,4);
 /* Match the last OBJ length and staging offset without relying on generation IDs. */
 unsigned slot = desc == 0x04c00020u;
 uint16_t *selected = slot ? &log->score : &log->selected;
 bool wanted = (slot || desc==0x04a00020u) && r->obj>=40 && !r->dirty &&
               tick>=5600 && tick<5750 && !*selected;
 if(mode900!=3 && !wanted && native_runtime165.receiver &&
    native_runtime165.receiver->state==NES_NATIVE165_COMPLETE){
  pending950=r;start950=t;return;
 }
 if(mode900!=3 && header950(r)){
   r->valid|=4;
   if(wanted && (r->valid&3)==3 && r->descriptor[0]==1 && r->descriptor[1]==1 &&
      r->wire[4] && r->wire[4]<=128 && r->wire[5] && r->wire[5]<=32 && a<65535){
''' + s[end:]
    s = s.replace('log->sample[group*256+j]', 'log->sample[slot*160+group*128+j]')
    start, end = s.index('    log->commit_age915='), s.index('   }\n }\ntrace_done:')
    s = s[:start]+'''    uint32_t gap=(ack900.clock-previous_ack956)>>9;
    uint16_t interval=gap>65534 ? 65535 : gap;
    if(slot)log->query_age915=interval;else log->commit_age915=interval;
    *selected=log->used;
'''+s[end:]
    s = s.replace('void e0900(', 'static uint32_t previous_ack956;\nvoid e0900(')
    s = s.replace('if(!ack900.valid || ack900.gen!=g)ack900=',
                  'if(!ack900.valid || ack900.gen!=g){previous_ack956=ack900.clock;ack900=')
    s = s.replace('1+(bank<<1)};', '1+(bank<<1)};}')
    assert s.count('log900p->edition=955;') == 1
    (SOURCE/'nes_budget210.c').write_text(s.replace('log900p->edition=955;', 'log900p->edition=956;'), newline='\n')


if __name__=='__main__':
    prepare()
