"""Bound late tile work by its existing160B size; retain BG priority before OBJ."""
import argparse,json,shutil
from pathlib import Path
from build_nes_trace_replay import Code
from prepare_nes_progress680 import client,ORIGIN
from nes_progress680_scan import scan
from nes_raw506 import once,sha


def receiver(body,labels,map_first=False):
    body,labels=scan(body,labels,neighbor=True)
    body=bytearray(body);c=Code(ORIGIN+len(body));c.labels.update(labels)
    c.label('late_tile681');c.emit(0xc2,0x20)
    if map_first:c.absolute(0xae,0x1252)
    c.emit(0x98,0xc9,161,0);c.branch(0xb0,'large_tile681')
    c.emit(0xe2,0x20);c.jump('map_beam_ok526')
    c.label('large_tile681');c.jump('defer_beam' if map_first else 'late_map680')
    # This fallback is reached only after the real225..252-line latch and
    # only for a selected tile. Preserve selected X/Y and all STOP/head checks.
    old=bytes([0x4c])+(labels['defer_beam' if map_first else 'late_map680']&65535).to_bytes(2,'little')
    at=labels['no_map680']-ORIGIN if map_first else body.index(old,labels['selected526']-ORIGIN,labels['map_beam_ok526']-ORIGIN)
    assert body[at:at+3]==old
    body[at:at+3]=bytes([0x4c])+(c.labels['late_tile681']&65535).to_bytes(2,'little')
    body.extend(c.finish());assert len(body)<=5984
    return body,c.labels


def arm(base,out,zero_boundary=False):
    ref=json.loads(Path('analysis/progress680-verification.json').read_text())
    assert sha(base/'src/obj-nes-100/firmware.stm')==ref['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_plan_service200.c';s=p.read_text()
    s=once(s,'if(mode==NES_MAP553 && p->bank_history==2 && p->window && p->window->last[1]==2){',
        '''/* Finish/query the ready BG producer before deferring it behind a
  * warm map run. Once checked ownership has reached OBJ, retain678's map
  * priority, bulk receipt and four-credit bound. No split or timed wait. */
 if(mode==NES_MAP553 && p->bank_history==2 && p->window && p->window->last[1]==2 &&
    p->bulk_valid && p->bulk[1]){''')
    if zero_boundary:
        # A nonzero BG already handed off is not a reason to poll between
        # every map packet. Only the fixed zero-tile producer boundary opens
        # this handoff; retain the normal checked map run afterward.
        s=once(s,'p->bulk_valid && p->bulk[1]){',
               'p->bulk_valid && (p->bulk[1] || p->bulk[4] || p->bulk[5])){')
    p.write_text(s,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base-client','client','base-arm','arm'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--zero-boundary',action='store_true')
    p.add_argument('--map-first',action='store_true')
    a=p.parse_args();arm(a.base_arm,a.arm,a.zero_boundary);r=client(a.base_client,a.client,extra_edit=lambda b,l:receiver(b,l,a.map_first))
    r.update(candidate='late681-map-first' if a.map_first else 'late681',late_tile_max_B=160,map_last_line=252,extra_DMA_stack_B=3)
    (a.client/'build.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('body_bytes','body_free','prefix_B','physical_free_B')}))
