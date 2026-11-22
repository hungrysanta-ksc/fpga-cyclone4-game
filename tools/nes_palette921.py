"""Measure the first palette head alongside MMC920's two checked OBJ responses."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_return920 import LeadingRecord, PROBES, arm, client, once, peer, trace
from replay_nes_supply905 import joint, UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3

WORK = PROBES / 'nes-palette921'
MODES = ('baseline', 'first', 'split', 'prefix', 'stream', 'queued', 'handoff', 'pair', 'bounded',
         'fixed', 'overlap', 'tail', 'compact')


def image(mode):
    return arm('reference' if mode == 'baseline' else 'first') if mode in MODES[:2] else WORK / mode


def prepare(mode):
    if mode in ('baseline','first'):
        raise ValueError('control images use the archived final links')
    link = image(mode) / 'link'
    shutil.copytree(arm('first') / 'link', link)
    def edit(file, changes):
        path = link / 'src' / file
        s = path.read_text()
        for old, new in changes:
            s = once(s, old, new)
        path.write_text(s, newline='\n')
    sink = 'nes_native_sink165.c'
    changes = [('bool split=span_cost227(b,n)&1;', 'bool split=section==3 || (span_cost227(b,n)&1);'),
               ('static bool fail(struct nes_native_sink165','static __attribute__((cold,noinline)) bool fail(struct nes_native_sink165')]
    if mode in ('prefix', 'stream', 'queued', 'pair', 'bounded'):
        edit('nes_native_video165.h', [('bool scroll_issued;', 'uint8_t scroll_issued;')])
        edit('nes_native_sink165.h', [('bool nes_sink212_seal(', 'bool nes_palette921(struct nes_native_sink165 *,struct nes_native_video165 *);\nbool nes_sink212_seal(')])
        planner = 'nes_planner211.c'
        s = (link / 'src' / planner).read_text()
        finish = s[s.index(' if(p->scroll_issued && resident->finish_obj'):s.index(' /* CGRAM becomes')]
        colors = s[s.index(' memset(p->cgram,'):s.index('\n if(p->patch_count){\n  /* No BG')]
        # The final OBJ rank no longer owns CGRAM. The raw-layer fill below
        # writes only bytes 128..255, disjoint from the immutable prefix.
        edit(planner, [(finish, ''), (colors, colors+finish)])
        edit('nes_native_runtime165.c', [('return p->sent || !p->count || p->count>=14 || p->bytes>208 || nes_plan200_end(p);',
            'if(!p->sent && p->count && p->count<14 && p->bytes<=208 && !nes_plan200_end(p))return false;\n return nes_palette921(&s->sink,s->video);')])
        changes.extend([('static bool oam227(','''bool nes_palette921(struct nes_native_sink165 *s,struct nes_native_video165 *p){
 /* Full palette is mandatory if a bank is cold or the prefix changed.
  * The current scroll was queued. Only the normal checked enqueue commits it. */
 if(s->plan->bank_history!=2 || !p->patch_count ||
    (s->ack635[0] && s->ack635[1] && !memcmp(s->palette635,p->cgram,32)))return true;
 if(!packet(s,2,3,0,p->cgram,32))return false;
 p->scroll_issued=2;
 return true;
}
static bool oam227('''),
            ('if(!span(s,3,0,p->cgram,512))return false;', '''unsigned prefix=p->scroll_issued==2?32:0;
 if(!span(s,3,prefix,p->cgram+prefix,512-prefix))return false;''')])
    if mode in ('stream', 'queued', 'handoff', 'pair', 'bounded', 'fixed', 'overlap','tail','compact'):
        # Emit from the immutable source. Four-byte repeats still require a
        # bytewise match; staging, CRC and checked bank retirement are unchanged.
        changes += [
            (' unsigned cost=(first?(span_cost227(b,first)>>1):0)+471+8*4+(span_cost227(b+512,32)>>1);',''),
            ('length<64||repeat_bytes(b+first,length)==length||cost>=(span_cost227(b,544)>>1)',
             'length<128||!memcmp(b+508,b+510,2)'),
            ('&&span(s,4,512,b+512,32)', '&&packet(s,2,4,512,b+512,32)'),
            ('   for(unsigned sample=0;sample<4;sample++)\n    if(!nes_window184_drain',
             '   if(!nes_window184_drain')]
    if mode in ('queued','pair','bounded'):
        # At the planner callback END may still be unpublished. The ordinary
        # FINISH arbiter requires END; use the existing direct DATA selector.
        # Leave space for the checked tile receipt in the four-head window.
        changes += [(' if(!packet(s,2,3,0,p->cgram,32))return false;',
                     ''' struct nes_plan200 *plan=s->plan;
 if(!plan->window || (plan->bulk_pending &&
     (uint16_t)(plan->window->sent-plan->bulk_until)>=3))return true;
 if(!packet(s,24,3,0,p->cgram,32))return false;''')]
    if mode in ('pair','bounded'):
        changes += [('(uint16_t)(plan->window->sent-plan->bulk_until)>=3',
                     '(uint16_t)(plan->window->sent-plan->bulk_until)>=2'),
                    ('if(!packet(s,24,3,0,p->cgram,32))return false;',
                     '''if(!packet(s,24,3,0,p->cgram,32) ||
    !packet(s,24,3,32,p->cgram+32,96))return false;'''),
                    ('p->scroll_issued==2?32:0', 'p->scroll_issued==2?128:0')]
    if mode == 'bounded':
        # Bound the first packet's CPU cost in each section and remove the
        # duplicated full-span search from the Flash image.
        changes += [('bool split=section==3 || (span_cost227(b,n)&1);','bool split=true;')]
    if mode in ('handoff','fixed','overlap','tail','compact'):
        # Only the directly preceding, checked OBJ is outstanding. Publish
        # one palette head before querying its successor. The next ordinary
        # head and SEAL both use the original E8/receipt path.
        changes += [(' if(s->plan && op>=2',
                     ''' if(op==2 && section==3 && !at && s->plan && s->plan->bulk_pending &&
    s->plan->bulk[1] && s->plan->bulk_until==s->plan->window->sent)op=24;
 if(s->plan && op>=2''')]
    if mode in ('fixed','overlap','tail'):
        # The four intervals cover all 512 bytes. No assumption of zero or
        # prior-bank validity: packet() tests the actual bytes on every send.
        changes += [('if(!span(s,3,0,p->cgram,512))return false;',
                     '''if(s->plan && s->plan->bulk_pending && s->plan->bulk[1] &&
    !r->map_upload && p->scroll_issued && p->patch_count==1){
  const uint8_t *pal=p->cgram;
  if(!packet(s,2,3,0,pal,32) || !packet(s,2,3,32,pal+32,96) ||
     !packet(s,2,3,128,pal+128,232) || !packet(s,2,3,360,pal+360,152))return false;
 }else if(!span(s,3,0,p->cgram,512))return false;''')]
    if mode in ('overlap','tail'):
        changes += [('!packet(s,2,3,128,pal+128,232)',
                     '''!packet(s,s->plan->bulk_pending &&
       (uint16_t)(s->plan->window->sent-s->plan->bulk_until)<2?24:2,3,128,pal+128,232)'''),
                    ('if(section==3 && at==128 && s->plan', 'if(op!=24 && section==3 && at==128 && s->plan')]
    if mode=='tail':
        changes += [('!packet(s,2,3,360,pal+360,152)',
                     '''!packet(s,s->plan->bulk_pending &&
       (uint16_t)(s->plan->window->sent-s->plan->bulk_until)<3?24:2,3,360,pal+360,152)''')]
    if mode=='compact':
        changes += [
            ('bool split=section==3 || (span_cost227(b,n)&1);',
             '''static const uint8_t palette_sizes[]={32,96,232,152};
 unsigned piece=0;
 bool fixed=section==3 && n==512 && s->plan && s->plan->bulk_pending && s->plan->bulk[1];'''),
            ('if(split)count=span_piece(b+at,count);else if(count>240)count=240;',
             'count=fixed?palette_sizes[piece++]:span_piece(b+at,count);'),
            ('if(op==2 && section==3 && !at && s->plan && s->plan->bulk_pending &&\n    s->plan->bulk[1] && s->plan->bulk_until==s->plan->window->sent)op=24;',
             '''if(op==2 && section==3 && s->plan && s->plan->bulk_pending && s->plan->bulk[1]){
  unsigned age=(uint16_t)(s->plan->window->sent-s->plan->bulk_until);
  if((!at && !age) || (at>=128 && age<3))op=24;
 }'''),
            ('if(section==3 && at==128 && s->plan','if(op!=24 && section==3 && at==128 && s->plan')]
    edit(sink, changes)
    if mode in ('bounded','compact'):
        drop_unused_costs(link/'src'/sink)


def drop_unused_costs(path):
    s=path.read_text()
    for start, end in [('static unsigned data_cost','static unsigned span_piece'),
                       ('static unsigned span_cost227','static bool span(')]:
        s=s[:s.index(start)]+s[s.index(end,s.index(start)):]
    path.write_text(s,newline='\n')


def replay(temp, mode, phase, cold):
    marks = []
    original = joint.Runtime.__init__
    def attach(cpu, args, link):
        original(cpu, args, link)
        def observe(name):
            def mark(u, *unused):
                if cpu.generation != 908:
                    return
                a, b, c = (u.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3))
                if name=='span' and a!=3: return
                if name=='packet_wire' and b!=3: return
                if name=='nes_window184_enqueue':
                    head=bytes(u.mem_read(a,16))
                    if head[1]!=3: return
                    a,b,c=head[0],head[1],int.from_bytes(head[10:12],'little')
                marks.append([name,round(cpu.clock),a,b,c])
            return mark
        for name in ('span','packet_wire','nes_window184_enqueue','nes_sink212_seal','finish_obj810'):
            addr=cpu.syms[name]
            cpu.u.hook_add(UC_HOOK_CODE,observe(name),begin=addr,end=addr)
    rom=client('reference' if mode=='baseline' else 'first')
    tag='921'+mode
    with patch.object(joint.Runtime,'__init__',attach), patch.object(peer,'PeerLink',LeadingRecord), patch.object(peer,'CLIENT',rom), patch.object(peer,'monitor',trace):
        peer.compare(temp,phase,cold,True,edition=915,work_arm=image(mode),run_id=tag)
    folder=temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{"cold" if cold else "warm"}-pair'
    (folder/'arm921.json').write_text(json.dumps(marks))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','replay','proof','guards'))
    parser.add_argument('mode',choices=MODES)
    parser.add_argument('temp',type=Path,nargs='?')
    parser.add_argument('phase',type=int,nargs='?')
    parser.add_argument('--cold',action='store_true')
    args=parser.parse_args()
    if args.action=='prepare':
        prepare(args.mode)
    elif args.action=='proof':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',image(args.mode),915)
    elif args.action=='guards':
        from nes_return920 import guards
        guards(args.temp,'first',tag='921'+args.mode,destination=WORK/(args.mode+'-guards.json'))
    else:
        replay(args.temp,args.mode,args.phase,args.cold)
