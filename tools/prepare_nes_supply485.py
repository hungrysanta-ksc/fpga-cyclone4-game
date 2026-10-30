# SPDX-License-Identifier: MIT
"""484 ARM -> first-BG release and explicitly tracked async bulk submission.

No FPGA/wire/client change. Finish drains real ACK before SEAL; duplicate token
snapshots cannot re-enqueue bulk. Legacy blocking bulk API remains available.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def once(s, old, new):
    assert s.count(old) == 1, old[:120]
    return s.replace(old, new)


def transform(name, s, joint=True):
    if name == 'nes_plan_service200.h':
        s = once(s, ' uint8_t buffer[248];', ''' bool early;
'''+(''' struct nes_sink_window184 *window;
 uint8_t bulk[12];bool bulk_valid,bulk_pending;
''' if joint else '')+''' uint8_t buffer[248];''')
    if name == 'nes_plan_service200.c':
        s = once(s, '#include <string.h>', '#include <string.h>\n#include "nes_sink_window184.h"')
        if joint:
            s = once(s, 'static bool poll(struct nes_plan200 *p,', '''static bool wait485(struct nes_plan200 *p){
 return !p->window||!p->window->wait||p->window->wait(p->window->ctx,p->window->guard,0,false)||fail(p,2);
}
static bool complete485(struct nes_plan200 *p){
 if(!p->bulk_pending)return true;
 uint8_t ack[12];
 if(!p->window||p->window->last[0]!=7||!nes_window184_drain(p->window,ack))return fail(p,5);
 p->bulk_pending=false;return true;
}
static uint32_t token485(const uint8_t *d){
 return (uint32_t)d[8]|(uint32_t)d[9]<<8|(uint32_t)d[10]<<16|(uint32_t)d[11]<<24;
}
static bool poll(struct nes_plan200 *p,''')
            old = '''  if(!p->guard(p->ctx)||!nes_sink195_bulk(p->sink,rx+6))return fail(p,5);
  *flags=0;'''
            s = once(s, old, '''  if(!p->guard(p->ctx))return fail(p,2);
  if(!p->window){if(!nes_sink195_bulk(p->sink,rx+6))return fail(p,5);}
  else {
   const uint8_t *d=rx+6;
   if(p->bulk_valid&&token485(d)==token485(p->bulk)){
    if(memcmp(d,p->bulk,12))return status215(p,phase,NES_PLAN215_DESCRIPTOR,rx);
    if(phase==NES_PLAN215_FINISH&&!complete485(p))return false;
    *flags=0;return true;
   }
   if(p->bulk_valid&&token485(d)<token485(p->bulk))return status215(p,phase,NES_PLAN215_DESCRIPTOR,rx);
   if(!complete485(p)||!nes_sink195_submit(p->sink,d))return fail(p,5);
   memcpy(p->bulk,d,12);p->bulk_valid=p->bulk_pending=true;
   if(phase==NES_PLAN215_FINISH&&!complete485(p))return false;
  }
  *flags=0;''')
            s = once(s, '  *flags=rx[3];', '  if((rx[3]&2)&&!complete485(p))return false;\n  *flags=rx[3];')
            s = once(s, '   p->sent++;p->bytes=0;p->count=0;return true;\n  }\n }',
                     '   p->sent++;p->bytes=0;p->count=0;return true;\n  }\n  if(!wait485(p))return false;\n }')
            s = once(s, '  if(flags&2){p->finished=true;return true;}\n }',
                     '  if(flags&2){p->finished=true;return true;}\n  if(!wait485(p))return false;\n }')
        s = once(s, 'p->started=true;p->generation=q->generation;return append(p,q);', '''p->started=true;p->generation=q->generation;
 if(!append(p,q))return false;
 if(!p->early&&q->kind==0){p->early=true;return flush(p);}
'''+(''' if(p->early&&p->window){uint8_t flags;if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;}
''' if joint else '')+''' return true;''')
        s = once(s, 'p->sent=0;p->finished=false;p->started=false;p->generation=0;return true;',
                 'p->sent=0;p->finished=false;p->started=false;p->generation=0;p->early=false;'+
                 ('p->bulk_valid=p->bulk_pending=false;' if joint else '')+'return true;')
    if joint and name == 'nes_native_runtime165.c':
        s = once(s, 's->plan.sink=&s->sink;', 's->plan.window=&s->transport;s->plan.sink=&s->sink;')
    if joint and name == 'nes_native_sink165.c':
        s = once(s, ' uint8_t b[256]={0},ack[12]={0};',
                 ' /*23 is an internal submission selector; wire opcode remains7. */\n bool bulk_submit=op==23;if(bulk_submit)op=7;\n uint8_t b[256]={0},ack[12]={0};')
        s = once(s, 'b[0]==6||b[0]==8)', 'b[0]==6||b[0]==8||bulk_submit)')
    if joint and name == 'nes_sink_window184.c':
        s = once(s, 'p[0]!=6&&p[0]!=8)', 'p[0]!=6&&p[0]!=8&&p[0]!=7)')
    if joint and name == 'nes_sink_bulk195.inc':
        s = once(s, 'bool nes_sink195_bulk(struct nes_native_sink165 *s,const uint8_t d[12]){',
                 'static bool bulk485(struct nes_native_sink165 *s,const uint8_t d[12],bool queued){')
        s = once(s, 'packet_wire(s,7,kind,offset,d+8,4,length)', 'packet_wire(s,queued?23:7,kind,offset,d+8,4,length)')
        s = s.replace(' /* packet_wire deliberately keeps op7 off the async enqueue path. */',
                      ' /* Counters are tentative issued coverage, never display completion. */')
        s += '''
bool nes_sink195_bulk(struct nes_native_sink165 *s,const uint8_t d[12]){return bulk485(s,d,false);}
bool nes_sink195_submit(struct nes_native_sink165 *s,const uint8_t d[12]){
 if(!s->enqueue)return fail(s,4);
 return bulk485(s,d,true);
}
'''
    if joint and name == 'nes_sink_bulk195.h':
        s = once(s, '#endif', '''/* Queued submission only. Caller retains descriptor ownership, suppresses
 * repeats, and drains the actual matching ACK before publishing finish/SEAL. */
bool nes_sink195_submit(struct nes_native_sink165 *,const uint8_t descriptor[12]);
#endif''')
    return s


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arm', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--eager-only', action='store_true')
    p.add_argument('--trial-labels', action='store_true')
    a = p.parse_args()
    reference = json.loads((ROOT/'analysis/game484-planner.json').read_text(encoding='utf8'))
    assert sha(a.arm/'obj-nes-100/firmware.stm') == reference['ARM']['firmware_SHA256']
    a.out.mkdir(parents=True, exist_ok=False)
    patch = a.out/'patch';patch.mkdir()
    base = {}
    for n in ['nes_plan_service200.h','nes_plan_service200.c','nes_native_runtime165.c',
              'nes_native_sink165.c','nes_sink_window184.c','nes_sink_bulk195.inc','nes_sink_bulk195.h']:
        q=a.arm/n;base[n]=sha(q);s=q.read_text(encoding='utf8');new=transform(n,s,not a.eager_only)
        if s!=new:(patch/n).write_text(new,encoding='utf8',newline='\n')
    if a.trial_labels:
        for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c']:
            q=a.arm/n;base[n]=sha(q);s=q.read_text(encoding='utf8')
            assert 'mmc482' in s
            s=s.replace('mmc482','mmc485').replace('MMC482','MMC485').replace('MMC3 482','MMC3 485')
            (patch/n).write_text(s,encoding='utf8',newline='\n')
    result={'scope':__doc__,'eager_only':a.eager_only,'trial_labels':a.trial_labels,'baseline_firmware_SHA256':reference['ARM']['firmware_SHA256'],
            'base_sources':base,'patch_sources':{q.name:sha(q) for q in patch.iterdir()},
            'FPGA_changed':False,'wire_ABI_changed':False,'hardware_verified':False}
    (a.out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'prepared':True,'eager_only':a.eager_only,'files':list(result['patch_sources'])}))
