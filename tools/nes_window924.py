"""Replay the open queue before an OAM fill and the checked final receipt separately."""
import argparse
import json
import shutil
from functools import partial
from pathlib import Path
from unittest.mock import patch

from nes_obj923 import WORK as PREVIOUS, obj_stops
from nes_return920 import LeadingRecord, PROBES, client, guards, once, peer, trace

BASE = PREVIOUS / 'warm'
WORK = PROBES / 'nes-window924'
FINAL = ('final', 'headerfit', 'jointfit', 'checked', 'object', 'safeheader', 'objheader')
SHORT_INITIAL_PAGE = ('headerfit', 'safeheader', 'objheader')
HEADER = ('fragment', *FINAL)
MODES = ('control', 'queue', 'receipt', 'both', 'fill', *HEADER)


def run_tag(mode):
    return '924'+mode


def prepare(mode):
    if mode=='control':
        raise ValueError('The control replays the existing 923 link directly.')
    link = WORK / mode / 'link'
    shutil.copytree(BASE / 'link', link)
    if mode != 'receipt':
        path = link / 'src/nes_native_sink165.c'
        s = path.read_text()
        decl = 'static __attribute__((noinline)) bool wait_map880(struct nes_sink_window184 *w,unsigned limit)'
        anchor = 'static bool packet_wire('
        s = once(s, anchor, decl + ';\n' + anchor)
        reads = 4 if mode in ('queue', 'both') else 12
        s = once(s, ' /* The original span still owns', f''' /* Let an already submitted OBJ return before issuing the OAM fill.
  * The existing idle consumer arbitrates STOP, new heads and beam limits.
  * The bounded wait is a scheduling opportunity, never proof of tile DMA. */
 if(op==8 && s->plan && s->plan->window->last[0]==7 &&
    !wait_map880(s->plan->window,{reads}))return fail(s,5);
 /* The original span still owns''')
        if mode in ('checked','object','safeheader','objheader'):
            condition='s->plan->window && s->plan->window->last[0]==7'
            if mode in ('object','objheader'):
                condition+=' && s->plan->window->last[1]==1'
            s=once(s, 'if(op==8 && s->plan && s->plan->window->last[0]==7',
                   'if(op==8 && s->plan && '+condition)
        path.write_text(s, newline='\n')
    if mode in ('fill', *HEADER):
        path = link / 'src/nes_sink_window184.c'
        s = path.read_text()
        begin = 'bool nes_window532_room('
        s = once(s, begin, '''static __attribute__((noinline)) bool receipt_matches(
 const struct nes_sink_window184 *s,const uint8_t *ack,unsigned status){
 return ack[0]==status && ack[1]==s->last[0] &&
        !memcmp(ack+2,s->last+2,8) && ack[10]==0x65 && ack[11]==0x9a;
}
''' + begin)
        start = s.index('(ack[0]!=0 ||')
        end = s.index('))return fail(s,8);', start)
        s = s[:start] + '!receipt_matches(s,ack,0)' + s[end+1:]
        start = s.index('(ack[0]!=(s->last[0]==3?1:0)')
        end = s.index('))return fail(s,8);', start)
        s = s[:start] + '!receipt_matches(s,ack,s->last[0]==3)' + s[end+1:]
        s = once(s, 'static bool fail(', 'static __attribute__((cold,noinline)) bool fail(')
        path.write_text(s, newline='\n')
    if mode != 'queue':
        path = link / 'src/nes_native_runtime165.c'
        s = path.read_text()
        # If D3 has already received a positive, CRC-checked D0, service the
        # offered COMMIT record in this step. poll() still checks token, CRC,
        # retirement and STOP through the original SRAM transport.
        s = once(s, ' }else if(r->state!=NES_NATIVE165_COMMITTED){',
                 '  if(r->ready183 && !nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);\n }else if(r->state!=NES_NATIVE165_COMMITTED){')
        path.write_text(s, newline='\n')
        path = link / 'src/nes_sink_window184.c'
        s = once(path.read_text(), 'return wait474(s,s->last[0]==3?2:1,true);',
                 'return s->last[0]==3 ? s->guard(s->ctx) : wait474(s,1,true);')
        path.write_text(s, newline='\n')
    if mode in HEADER:
        path = link / 'src/nes_budget210.c'
        s = path.read_text()
        a=s.index('int nes_budget210_format(')
        b=s.index(' for(unsigned i=0;i<12;i++){',a)
        # Both the packed writer and the hex-line writer propagate a negative
        # cursor before any output. Retain a single check before the bin loop.
        s=s[:a]+s[a:b].replace('if(n<0)return -1;','')+' if(n<0)return -1;\n'+s[b:]
        s=once(s, 'len>(size-(unsigned)n-1)/2 || size-(unsigned)n<2*len+2',
               'size-(unsigned)n<2 || len>(size-(unsigned)n-2)/2')
        path.write_text(s,newline='\n')
    if mode in HEADER:
        path=link/'src/nes_runtime_board165.inc'
        s=once(path.read_text(), 'native_io165,query,rx,sizeof query',
               'native_io165,query,rx,page>255 ? 16 : sizeof query')
        path.write_text(s,newline='\n')
        path=link/'src/nes_budget210.c'
        # The first sample consumes only the 16-byte header. Detailed pages
        # (including detail page zero) still need both 8-byte body records.
        flag='256' if mode in SHORT_INITIAL_PAGE else '(native_runtime165.sink.obj_next>=24 ? 256 : 0)'
        s=once(path.read_text(), 'mode900!=3 && page905(page,0)', 'mode900!=3 && page905(page,'+flag+')')
        path.write_text(s,newline='\n')
        path=link/'src/nes_cost471.c'
        s=path.read_text()
        a=s.index('int nes_cost471_append(')
        b=s.index(' return n;\n}',a)
        s=s[:a]+s[a:b].replace(' if(n<0)return -1;','')+s[b:]
        path.write_text(s,newline='\n')
    if mode in FINAL:
        # Reuse the checked packed writer outside RUN. Keep every original
        # format, argument, truncation limit and safe-return/file boundary.
        path=link/'src/nes_menu_diagnostic.c'
        s=path.read_text()
        s=once(s,'int n=nes_report594(text,4096,(const unsigned char *)',
               'int n=nes_packed828(text,4096,0,')
        for old,new in [
            ('int used=nes_report594(text+n,4096-(size_t)n,(const unsigned char *)','n=nes_packed828(text,4096,n,'),
            ('  n=used<0||(size_t)used>=4096-(size_t)n?-1:n+used;\n',''),
            ('extra=nes_report594(text+n,4096-(unsigned)n,(const unsigned char *)','n=nes_packed828(text,4096,n,'),
            (' if(extra<0||(unsigned)extra>=4096-(unsigned)n)return;\n n+=extra;',' if(n<0)return;')]:
            assert s.count(old)==2,old
            s=s.replace(old,new)
        path.write_text(s,newline='\n')
    if mode=='jointfit':
        path = link / 'src/nes_native_runtime165.c'
        s = path.read_text()
        # Only the final display receipt remains after all input data have
        # retired. Keep ordinary credit/IRQ pacing while either side is busy.
        quiet = '(s->sink.obj_next>=24 ? 0u : 84u*96u)'
        s = once(s, '84u*96u : 84u*128u', quiet+' : 84u*128u')
        path.write_text(s, newline='\n')


def replay(temp, mode, phase, cold):
    def monitor(source, scene):
        return once(trace(source, scene), 'pb(0)==7 and pw(8)==908', 'pb(0)==7 and pw(8)==909')
    cache = 'cold' if cold else 'warm'
    reference = temp / f'nes-tile821-obj-jointmirror-p{phase}-923warm-{cache}-pair'
    costs = json.loads((reference/'joint.json').read_bytes())['parameters']['driver_extra_us']
    with patch.object(peer, 'main', partial(peer.main, driver_extra_us=costs)), patch.object(peer, 'PeerLink', LeadingRecord), patch.object(peer, 'CLIENT', client('first')), patch.object(peer, 'monitor', monitor):
        peer.compare(temp, phase, cold, True, edition=915, work_arm=BASE if mode=='control' else WORK/mode, run_id=run_tag(mode))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'replay', 'guards', 'proof'))
    p.add_argument('mode', choices=MODES)
    p.add_argument('temp', type=Path, nargs='?')
    p.add_argument('phase', type=int, nargs='?', choices=(1, 2))
    p.add_argument('--cold', action='store_true')
    a = p.parse_args()
    if a.action == 'prepare':
        prepare(a.mode)
    elif a.action == 'replay':
        replay(a.temp, a.mode, a.phase, a.cold)
    elif a.action == 'guards':
        guards(a.temp, 'first', tag=run_tag(a.mode), destination=WORK/(a.mode+'-guards.json'))
        obj_stops(a.temp,a.mode,tag=run_tag(a.mode),destination=WORK/(a.mode+'-stops.json'))
    else:
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes', WORK/a.mode, 915,
            short_header=a.mode in SHORT_INITIAL_PAGE)
        if a.mode in FINAL:
            from check_nes_window924 import check
            stamp=check(BASE/'link/src',WORK/a.mode/'link/src')
            (WORK/(a.mode+'-report.json')).write_text(json.dumps(stamp,indent=2)+'\n')
