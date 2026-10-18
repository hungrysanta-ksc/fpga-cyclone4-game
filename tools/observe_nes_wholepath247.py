# SPDX-License-Identifier: MIT
"""Observe existing231 map/slot decisions; preserve every original replay output.

Private recorded SMB3 inputs and ROM are required. No product modification,
Questa/FIT, ARM timing, SNES replay or physical execution is performed here.
"""
from pathlib import Path
import argparse
import ctypes
import json
import os
import shutil
import subprocess
from nes_delta231 import BASE, sha, once
from run_nes_scroll229 import ROM_SHA


OBSERVER = r'''
static unsigned frame247;
static FILE *map247,*slot247;
void observe247_map(unsigned g,unsigned first,unsigned end,unsigned x,unsigned column,
                    unsigned at,unsigned old,unsigned value,const struct nes_plan191 *q){
 fprintf(map247,"%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,",frame247,g,first,end,x,column,at,old,value,q->tag);
 for(unsigned i=0;i<16;i++)fprintf(map247,"%x",q->row[i]);
 fprintf(map247,",");for(unsigned i=0;i<8;i++)fprintf(map247,"%04x",q->alt[i]);
 fprintf(map247,"\n");
}
void observe247_slot(unsigned kind,unsigned slot,unsigned tag,unsigned mask,
                     unsigned retain,unsigned equal,unsigned resident,unsigned old){
 fprintf(slot247,"%u,%u,%u,%u,%u,%u,%u,%u,%u\n",frame247,kind,slot,tag,mask,retain,equal,resident,old);
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rom', type=Path, required=True)
    p.add_argument('--gcc', type=Path, required=True)
    a = p.parse_args()
    d = a.out.resolve()
    assert not d.exists(), 'Use a new run directory; preserve failures.'
    assert sha(a.rom) == ROM_SHA
    prior = BASE / 'probes/nes-delta231/test07'
    evidence = json.loads((prior / 'result.json').read_text())
    assert evidence['passed'] and sha(prior/'host.c') == evidence['host_sha256']
    d.mkdir(parents=True)
    pins = {}
    for src in sorted(prior.iterdir()):
        if src.suffix in ('.c', '.h', '.inc', '.delta') or src.name == 'palette.bin':
            if src.name in evidence['evidence_files']:
                assert sha(src) == evidence['evidence_files'][src.name], src.name
            shutil.copyfile(src, d/src.name)
            pins[src.name] = sha(src)
    f = d/'host.c'
    s = once(f.read_text(), 'static unsigned input_bytes,input_blocks;', OBSERVER+'\nstatic unsigned input_bytes,input_blocks;')
    s = once(s, ' reset();\n for(unsigned frame=', ''' map247=fopen("map247.csv","w");slot247=fopen("slot247.csv","w");assert(map247&&slot247);
 fprintf(map247,"frame,group,first,end,x,column,at,old,value,tag,row,alt\\n");
 fprintf(slot247,"frame,kind,slot,tag,mask,retain,equal,resident,old\\n");
 reset();
 for(unsigned frame=''')
    s = once(s, '  receive230(argv[1],frame);', '  frame247=frame;receive230(argv[1],frame);')
    s = once(s, ' fclose(csv);source_faults231();', ' fclose(map247);fclose(slot247);fclose(csv);source_faults231();')
    f.write_text(s, encoding='utf-8', newline='\n')
    f = d/'nes_planner211.c'
    s = once(f.read_text(), '#include <stddef.h>', '''#include <stddef.h>
extern void observe247_map(unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,const struct nes_plan191 *);''')
    needle = '  map_word185(p,at,slot|((bank[g]*4+(cell>>13))<<10)|0x2000,d);'
    s = once(s, needle, '''  observe247_map(g,first[g],end[g],x,column,at,p->map[at]+256u*p->map[at+1],slot|((bank[g]*4+(cell>>13))<<10)|0x2000,&q);
'''+needle)
    f.write_text(s, encoding='utf-8', newline='\n')
    f = d/'nes_resident211.c'
    s = once(f.read_text(), '#include <string.h>', '''#include <string.h>
extern void observe247_slot(unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);''')
    s = once(s, ' if(!equal){', ' unsigned old247=kind?s->obj[slot]:s->bg[slot];\n if(!equal){')
    needle = ' if(q->kind!=2&&equal&&bit(s->resident[s->target],index)){s->hits++;return slot;}'
    s = once(s, needle, ' observe247_slot(q->kind,slot,q->tag,q->mask,retain,equal,bit(s->resident[s->target],index),old247);\n'+needle)
    f.write_text(s, encoding='utf-8', newline='\n')
    env = os.environ.copy()
    env['PATH'] = str(a.gcc.parent)+os.pathsep+env.get('PATH', '')
    files = ['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c',
             'nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
    def native_path(path):
        # The archived MinGW C fixture uses narrow fopen, unlike Python's paths.
        buf = ctypes.create_unicode_buffer(32768)
        n = ctypes.windll.kernel32.GetShortPathNameW(str(path.resolve()), buf, len(buf))
        assert 0 < n < len(buf) and buf.value.isascii(), 'ASCII/short path required by archived C fixture'
        return buf.value
    for label, cmd in [('build', [a.gcc, '-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe']),
                       ('run', [d/'host.exe',native_path(BASE/'probes/nes-geometry230/rtl02'),native_path(a.rom),905,975,native_path(d)])]:
        with (d/(label+'.log')).open('wb') as log:
            q = subprocess.run(list(map(str, cmd)), cwd=d, env=env, stdout=log,
                               stderr=subprocess.STDOUT, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
        output = (d/(label+'.log')).read_text(errors='replace')
        assert q.returncode == 0, output[-6000:]
    assert 'reference_checks=4066624' in output
    compared = []
    for f in range(905, 976):
        for ext in ('geometry','raw','metadata','packets','plans'):
            name = f'frame{f}.{ext}'
            assert sha(prior/name) == evidence['evidence_files'][name]
            assert (d/name).read_bytes() == (prior/name).read_bytes(), name
            compared.append(name)
    assert (d/'cost.csv').read_bytes() == (prior/'cost.csv').read_bytes()
    result = dict(passed=True, scope=__doc__, frames=71, exact_files=len(compared), cost_exact=True,
                  reference_checks=4066624, input_pins=pins,
                  observed_sources={n:sha(d/n) for n in files},
                  output_hashes={n:sha(d/n) for n in compared+['cost.csv','map247.csv','slot247.csv','build.log','run.log']},
                  runner_sha256=sha(Path(__file__)), physical=False, product_changed=False,
                  arm_timing=False, new_rtl=False, new_snes=False)
    (d/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','frames','exact_files','cost_exact','reference_checks')}))


if __name__ == '__main__':
    main()
