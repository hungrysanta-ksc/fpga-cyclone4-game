# SPDX-License-Identifier: MIT
"""Output231/232 linked RUN candidate; ingress remains227 for this gate.

Reserve source231 state, but do not pretend the unimplemented FPGA delta
transport is linked. No installable pair follows from a successful ARM link.
"""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import ROOT,BASE,sha,once,materialize
from nes_board181 import copy_pins


def runtime(s):
    s=once(s,' if(s->resident)nes_resident211_abort(s->resident);',
        ' if(s->resident)nes_resident211_abort(s->resident);\n if(s->dirty)nes_dirty231_abort(s->dirty);\n if(s->source){s->source->valid=false;s->source->fault=true;}')
    s=once(s,'nes_native_video211_plan(s->receiver,s->palette,s->video,s->resident)',
        'nes_native_video231_plan(s->receiver,s->palette,s->video,s->resident,s->dirty)')
    s=once(s,'nes_sink212_seal(&s->sink,s->video,s->resident)',
        'nes_sink231_seal(&s->sink,s->video,s->resident,s->dirty)')
    s=once(s,'uint32_t epoch,bool immutable){',
        'uint32_t epoch,bool immutable,struct nes_dirty231 *dirty,struct nes_source231 *source){')
    s=once(s,'||!epoch||!immutable)', '||!epoch||!immutable||!dirty||!source)')
    s=once(s,' s->receiver=r;s->video=v;s->palette=palette;',
        ' s->receiver=r;s->video=v;s->palette=palette;\n s->dirty=dirty;s->source=source;nes_dirty231_reset(dirty);nes_source231_reset(source);')
    return s


def header(s):
    s=once(s,'#include "nes_resident211.h"','#include "nes_delta231.h"')
    s=once(s,' struct nes_plan200 plan;',
        ' struct nes_plan200 plan;\n struct nes_dirty231 *dirty;struct nes_source231 *source;')
    return once(s,'uint32_t content_epoch,bool immutable);',
        'uint32_t content_epoch,bool immutable,struct nes_dirty231 *,struct nes_source231 *);')


def board(s):
    s=once(s,'struct nes_resident211 resident;} work;',
        'struct nes_resident211 resident;struct nes_dirty231 dirty;struct nes_source231 source;} work;')
    s=once(s,'&work.resident,content_epoch,true);','&work.resident,content_epoch,true,&work.dirty,&work.source);')
    return once(s,' native_runtime165.resident=NULL;',
        ' native_runtime165.dirty=NULL;native_runtime165.source=NULL;\n native_runtime165.resident=NULL;')


def prepare(out):
    prior=BASE/'probes/nes-repeat227/arm01'
    p=json.loads((prior/'preparation-repeat227.json').read_bytes());pins=p['copied']|p['changed']|p['added']
    copy_pins(prior,out,pins);src=out/'src';materialize(out/'delta231')
    for n in ['nes_native165.c','nes_native_sink165.c','nes_native_sink165.h','nes_planner211.c','nes_delta231.c','nes_delta231.h','nes_delta231_receiver.inc']:
        shutil.copyfile(out/'delta231'/n,src/n)
    for n,fn in [('nes_native_runtime165.c',runtime),('nes_native_runtime165.h',header),('nes_runtime_board165.inc',board)]:
        f=src/n;f.write_text(fn(f.read_text()),encoding='utf-8',newline='\n')
    f=src/'Makefile';f.write_text(once(f.read_text(),'nes_planner211.c nes_resident211.c','nes_planner211.c nes_delta231.c nes_resident211.c'),encoding='utf-8',newline='\n')
    for n in ('nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION'):
        f=src/n;f.write_text(f.read_text().replace('227','233'),encoding='utf-8',newline='\n')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
    added={f'src/{n}':sha(src/n) for n in ('nes_delta231.c','nes_delta231.h','nes_delta231_receiver.inc')}
    r=dict(copied=pins,changed=changed,added=added,public_sources={'tools/nes_runtime233.py':sha(Path(__file__))},
           scope=__doc__,source_state_reserved=36,dirty_state=124,ingress_delta_bound=False,hardware_package=False)
    (out/'preparation-runtime233.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');return r


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    r=prepare(p.parse_args().out);print(json.dumps({'changed':r['changed'],'added':r['added']},indent=2))
