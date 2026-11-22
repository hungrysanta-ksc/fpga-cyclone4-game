"""Offer complete palette and OAM after slot allocation and before raw conversion."""
import argparse
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_postobj916 import ARM, OUT, PROBES, LeadingRecord, monitor, peer
from nes_raw506 import once, sha

WORK = PROBES / 'nes-issue917'
BG = PROBES / 'nes-issue917-bg'
LEAD = PROBES / 'nes-issue917-lead'
PAIR = PROBES / 'nes-issue917-pair'


def prepare(work):
    assert sha(ARM/'link/src/obj-nes-100/firmware.stm').lower()=='98564fcd0f24e3d61eaccee021021a04fd48c45252bf14a676f79fa214e118a7'
    link = work / 'link'
    shutil.copytree(ARM / 'link', link)
    src = link / 'src'
    def edit(name, replacements):
        path = src / name
        s = path.read_text()
        for a,b in replacements:
            s = once(s, a, b)
        path.write_text(s, newline='\n')
    if work==PAIR:
        early_pair(edit, src)
        return
    if work in (BG,LEAD):
        palette_bg(edit, src)
        if work==LEAD:
            zero_first(edit)
        return
    edit('nes_native_sink165.h', [
        ('uint8_t disable_column;', 'uint8_t disable_column; bool early_color;'),
        ('bool nes_sink212_seal(', 'bool nes_offer917(struct nes_native_sink165 *,struct nes_native_video165 *, struct nes_resident211 *);\nbool nes_sink212_seal(')])
    cb = ''' if(p->scroll_issued && resident->finish_obj && !resident->finish_obj(resident->ctx))
  return fail(p,7);'''
    # Rank and slot evaluation has finished. The immutable palette includes
    # the raw layer, and the scratch cleared below is disjoint from OAM/CGRAM.
    fill = 'for(unsigned c=0;c<64;c++)put16(p->cgram+(64+c)*2,lut[c]);'
    edit('nes_planner211.c', [(cb, ''), ('  '+fill,''),
        (' if(p->patch_count){\n  /* No BG', ' if(p->patch_count)'+fill+'\n'+cb+'\n if(p->patch_count){\n  /* No BG')])
    edit('nes_native_runtime165.c', [
        ('return p->sent || !p->count || p->count>=14 || p->bytes>208 || nes_plan200_end(p);',
         '''if(!p->sent && p->count && p->count<14 && p->bytes<=208 && !nes_plan200_end(p))return false;
 return nes_offer917(&s->sink,s->video,s->resident);''')])
    palette = '''if(!span(s,3,0,p->cgram,512))return false;
 if(!oam227(s,p->oam))return false;'''
    edit('nes_native_sink165.c', [
        ('s->strip_dma_seen=false;', 's->early_color=false;s->strip_dma_seen=false;'),
        ('if(s->plan && op>=2', 'if(!(s->early_color && !s->plan->bulk_pending && section>=3 && section<=5) && s->plan && op>=2'),
        ('   for(unsigned sample=0;sample<4;sample++)\n    if(!nes_window184_drain', '   if(!nes_window184_drain'),
        (palette,'if(!s->early_color && !colors917(s,p))return false;'),
        ('bool nes_sink212_seal(', '''static bool colors917(struct nes_native_sink165 *s,const struct nes_native_video165 *p){
 return span(s,3,0,p->cgram,512) && oam227(s,p->oam);
}
bool nes_offer917(struct nes_native_sink165 *s,struct nes_native_video165 *p,struct nes_resident211 *r){
 /* No pending map, complete OBJ slots, and no eligible two-bank reuse.
  * Retire an owned bulk before lending its receipt window to ordinary heads. */
 if((p->map_dirty|r->map_stale[r->target]) ||
    (s->ack635[0] && s->ack635[1] && same635(s,p)))return true;
 if(s->plan->bulk_pending){
  uint8_t ack[12];
  if(!nes_window184_through(s->plan->window,ack,s->plan->bulk_until))return false;
  s->plan->bulk_pending=false;
 }
 s->early_color=true;
 return colors917(s,p);
}
bool nes_sink212_seal(''')])


def palette_bg(edit, src):
    # CGRAM has no reader in map/OBJ allocation. Move its complete construction
    # before the first zero-tile offer, including the raw-layer lookup colors.
    name='nes_planner211.c'
    orig=(src/name).read_text()
    colors=orig[orig.index(' memset(p->cgram,'):orig.index('\n if(p->patch_count){\n  /* No BG')]
    raw='  for(unsigned c=0;c<64;c++)put16(p->cgram+(64+c)*2,lut[c]);'
    pivot=' /* Slot0 is explicitly zero'
    edit(name,[(colors,''),(raw,''),(pivot,colors+' if(p->patch_count)'+raw.strip()+'\n'+pivot)])
    edit('nes_native_sink165.h',[
        ('uint8_t disable_column;','uint8_t disable_column; bool early_palette;'),
        ('bool nes_sink212_seal(','bool nes_palette917(struct nes_native_sink165 *,struct nes_native_video165 *);\nbool nes_sink212_seal(')])
    edit('nes_native_runtime165.c',[
        ('nes_budget210_plan(q);return true;',
         '''nes_budget210_plan(q);
 return q->kind!=2 || nes_palette917(&s->sink,s->video);''')])
    edit('nes_native_sink165.c',[
        ('s->strip_dma_seen=false;', 's->early_palette=false;s->strip_dma_seen=false;'),
        ('if(s->plan && op>=2', 'if(!(s->early_palette && section==3) && s->plan && op>=2'),
        ('   for(unsigned sample=0;sample<4;sample++)\n    if(!nes_window184_drain','   if(!nes_window184_drain'),
        (' if(!span(s,3,0,p->cgram,512))return false;', ' if(!s->early_palette && !span(s,3,0,p->cgram,512))return false;'),
        ('static bool oam227(','''bool nes_palette917(struct nes_native_sink165 *s,struct nes_native_video165 *p){
 /* No tile descriptor has been borrowed at the first zero-slot offer.
  * Both ACKs are required for the ordinary reuse command; if either is
  * missing, the full palette is already mandatory irrespective of OAM. */
 if(s->plan->bank_history!=2 || (s->ack635[0] && s->ack635[1]) || s->plan->bulk_pending || !p->patch_count)return true;
 s->early_palette=true;
 return span(s,3,0,p->cgram,512);
}
static bool oam227(''')])


def early_pair(edit, src):
    # Both raw conversion and CGRAM are independent of OBJ allocation.
    # The planner's OBJ rank/evaluation scratch must not overwrite the patch.
    planner='nes_planner211.c'
    source=(src/planner).read_text()
    raw=source[source.index(' /* CGRAM becomes'):source.index(' p->valid=true;return true;')]
    pivot=' /* No OBJ/raw operation below writes map.'
    edit(planner,[(raw,''),(pivot,raw.replace(' /* CGRAM becomes the palette only after the final OBJ ACK. */',
        ' /* BG keys are dead. Build the immutable raw layer and palette before evaluating OBJ. */')+pivot),
        ('uint8_t *rank_used=(uint8_t *)p->bg_keys,','uint8_t *rank_used=(uint8_t *)p->bg_keys+3072,')])
    edit('nes_native_video165.h',[('bool scroll_issued;', 'uint8_t scroll_issued;')])
    sink='nes_native_sink165.c'
    s=(src/sink).read_text()
    pack=s[s.index('  unsigned packed=2048;'):s.index('\n bool same=same635')]
    tables=s[s.index('  _Static_assert(__builtin_offsetof(struct nes_native_video165,patch.enable)'):s.index('  unsigned prefix=packed-192;')]
    joined=s[s.index('  uint8_t *joined='):s.index('  offset+=192;')]
    helper='''static bool tail917(struct nes_native_sink165 *s,struct nes_native_video165 *p,unsigned *position,bool early){
  unsigned offset=*position;
'''+pack+tables+'''
  unsigned prefix=packed-192;
  if(prefix && !span(s,5,offset,raw,prefix))return false;
  offset+=prefix;
'''+joined.replace('packet(s,2,','packet(s,early?24:2,')+'''
  *position=offset+192;
  return true;
}
'''
    end=s[s.index('  _Static_assert(__builtin_offsetof(struct nes_native_video165,patch.enable)'):s.index('  put16(descriptor+10,offset+249);')]
    edit(sink,[(pack,''),
        (end,'''  if(p->scroll_issued==2)offset+=192;
  else if(!tail917(s,p,&offset,false))return false;
'''),
        ('bool nes_scroll810(',helper+'bool nes_scroll810('),
        ('static bool packet_wire(', 'enum { EARLY_PALETTE917=131 };\nstatic bool packet_wire('),
        ('if(s->plan && op>=2', 'if(section!=EARLY_PALETTE917 && s->plan && op>=2'),
        (' if(section==3 && at==128', ' if(section==EARLY_PALETTE917)section=3;\n if(section==3 && at==128'),
        (' if(!span(s,3,0,p->cgram,512))return false;', ' if(p->scroll_issued!=2 && !span(s,3,0,p->cgram,512))return false;'),
        (' p->scroll_issued=true;\n return true;', ''' p->scroll_issued=true;
 /* Scroll and its padding are committed to the queue. No borrowed tile
  * receipt or remaining map can lose its slot. A single raw row has
  * exactly two tail heads and no variable-length prefix. */
 if(!map && p->patch_count==1 && !(s->ack635[0] && s->ack635[1])){
  unsigned at=1121;
  if(!span(s,EARLY_PALETTE917,0,p->cgram,512) || !tail917(s,p,&at,true))return false;
  p->scroll_issued=2;
 }
 return true;'''),
        ('   for(unsigned sample=0;sample<4;sample++)\n    if(!nes_window184_drain','   if(!nes_window184_drain')])


def zero_first(edit):
    # One-palette compact-RGB layout has two proven zero intervals. Use
    # checked DATA writes for every interval, including the two fills.
    edit('nes_native_runtime165.c', [
        ('return q->kind!=2 || nes_palette917(&s->sink,s->video);',
         'return q->kind!=2 || s->receiver->counts[5]!=32 || nes_palette917(&s->sink,s->video);')])
    edit('nes_native_sink165.c', [
        (' s->early_palette=true;\n return span(s,3,0,p->cgram,512);',
         ''' if(!nes_plan549_first(s->plan))return false;
 bool room;
 if(!nes_plan527_map_credit(s->plan,&room))return false;
 if(s->plan->bulk_pending){
  uint8_t ack[12];
  if(!nes_window184_through(s->plan->window,ack,s->plan->bulk_until))return false;
  s->plan->bulk_pending=false;
 }
 s->early_palette=true;
 return packet(s,2,3,0,p->cgram,32) && packet(s,2,3,32,NULL,96) &&
        packet(s,2,3,128,p->cgram+128,232) && packet(s,2,3,360,NULL,152);'''),
        ('unsigned cost=(first?(span_cost227(b,first)>>1):0)+471+8*4+(span_cost227(b+512,32)>>1);',
         '''/* A long run of alternating unlike words fits the OAM tail opcode.
  * Short or single-word runs keep the full span encoder. */
 '''),
        ('length<64||repeat_bytes(b+first,length)==length||cost>=(span_cost227(b,544)>>1)',
         'length<128||!memcmp(b+508,b+510,2)'),
        ('&&span(s,4,512,b+512,32)', '&&packet(s,2,4,512,b+512,32)'),
        ('static bool fail(struct nes_native_sink165', 'static __attribute__((cold,noinline)) bool fail(struct nes_native_sink165')])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','guards'))
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,nargs='?',choices=(1,2))
    p.add_argument('--cold',action='store_true')
    variant=p.add_mutually_exclusive_group()
    variant.add_argument('--bg',action='store_true')
    variant.add_argument('--lead',action='store_true')
    variant.add_argument('--pair',action='store_true')
    a=p.parse_args()
    work,tag=(PAIR,'917pair') if a.pair else (LEAD,'917lead') if a.lead else (BG,'917bg') if a.bg else (WORK,'917issue')
    if a.action=='prepare':
        prepare(work)
    elif a.action=='guards':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work,915)
    else:
        with patch.object(peer,'PeerLink',LeadingRecord), patch.object(peer,'CLIENT',OUT/'consumer'), patch.object(peer,'monitor',monitor):
            peer.compare(a.temp,a.phase,a.cold,True,edition=915,work_arm=work,run_id=tag)


if __name__=='__main__':
    main()
