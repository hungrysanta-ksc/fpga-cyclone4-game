"""Service checked OBJ bank returns on the 922 firstrow ARM link."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_deadline922 import WORK as PREVIOUS
from nes_return920 import LeadingRecord, PROBES, client, guards, once, peer, trace

BASE=PREVIOUS/'firstrow'
WORK=PROBES/'nes-obj923'
MODES=('repoll','drain','chain','receipt','lookahead','ordered','preack','preall','preobj','split','prefix','paired','pairidle','mixed','mixedack','probe','nextbank','warm')


def prepare(mode):
    link=WORK/mode/'link'
    shutil.copytree(BASE/'link',link)
    path=link/'src/nes_plan_service200.c'
    s=path.read_text()
    checked_first=mode in ('preall','paired','pairidle','mixedack','probe','nextbank')
    if checked_first or mode in ('preack','preobj','warm'):
        old=' if(!read509(p,rx,phase))return false;'
        condition={'preack':'p->bulk[1] && p->bulk[2]==32 && !p->bulk[3] && ',
                   'preobj':'p->bulk[1] && ','warm':'p->bank_history==2 && '}.get(mode,'')
        s=once(s,old,' if('+condition+'!complete485(p))return false;\n'+old)
        if checked_first:
            # No path from the receipt to this snapshot submits another head.
            for redundant in ('    if(phase==NES_PLAN215_FINISH&&!complete485(p))return false;\n',
                              '   if(!complete485(p))return false;\n   /* A new ready tile',
                              '  if((rx[3]&2)&&!complete485(p))return false;\n'):
                s=once(s,redundant,'   /* A new ready tile' if '/*' in redundant else '')
    if mode in ('repoll','chain'):
        old='  if(!wait485(p))return false;\n }\n return fail(p,6);\n}\n\nbool nes_plan200_retire'
        s=once(s,old,old.replace('if(!wait485(p))','if(!(flags&4) && !wait485(p))'))
    if mode in ('drain','chain'):
        old='(mode==NES_MAP553 || mode==NES_ORDINARY553) && p->bulk_pending &&'
        s=once(s,old,'(mode==NES_MAP553 || (mode==NES_ORDINARY553 && !p->bulk[1])) && p->bulk_pending &&')
    if mode=='receipt':
        # through() itself checked the E0 identity, sent/retired and STOP.
        # No planner can submit another descriptor until poll returns.
        path=link/'src/nes_sink_window184.c'
        s=once(path.read_text(),'return wait474(s,s->last[0]==3?2:1,true);',
               'return s->last[0]==7 ? s->guard(s->ctx) : wait474(s,s->last[0]==3?2:1,true);')
    if mode in ('lookahead','ordered','split','prefix','paired','pairidle','mixed','mixedack','probe','nextbank','warm'):
        # Sort compact OBJ writes to distinct destinations in the existing
        # staging array. Equal destinations retain insertion order. Hardware
        # still sees at most 15 records and a checked token per physical bank.
        at=' if(p->count==15||p->bytes+n>240)if(!flush(p))return false;'
        split=''' if(p->count>=15 && !p->obj_start && (p->count==29 || encoded[0]!=0x81)){
  unsigned cut=15;
  CUT
  unsigned keep=p->count-cut;
  uint8_t *records=p->buffer+4;
  uint8_t saved[4];
  memcpy(saved,records+cut*8,4);
  p->count=cut;p->bytes=cut*8;
  if(!flush(p))return false;
  memcpy(records+cut*8,saved,4);
  memmove(records,records+cut*8,keep*8);
  p->count=keep;p->bytes=keep*8;
 }
 if(p->bytes+n>240 && !flush(p))return false;'''
        boundary='''while(cut<p->count && cut+14>p->count && cut>1 &&
        p->buffer[4+cut*8+3]==p->buffer[4+(cut-1)*8+3]+1)cut--;'''
        if mode=='split':
            # A BG and one compact OBJ can start filling the two banks while
            # the remaining, non-adjacent OBJ slots are sorted.
            split=''' if(encoded[0]==0x81 && p->count==2 && p->obj_start==7 &&
    p->bytes==15 && (unsigned)(q->slot+1-p->buffer[14])>2 && !flush(p))return false;
'''+split
        if mode in ('mixed','mixedack'):
            # A ZERO plan is three bytes. obj_start identifies the actual
            # prefix, whether it is ZERO or a ROM-backed BG. Only the single
            # prefix immediately followed by 14 compact OBJ plans can spill.
            split=split.replace('!p->obj_start && (p->count==29','(p->obj_start || p->count==29')
            split=split.replace('unsigned cut=15;', '''unsigned cut=p->obj_start?1:15;
  unsigned bytes=p->obj_start?p->obj_start:120;''').replace('cut*8','bytes')
        s=once(s,at,split.replace('CUT',boundary if mode=='ordered' else ''))
        a=s.index(' if(p->count<15)return true;',s.index('static bool append('))
        b=s.index(' return flush(p);',a)
        tail=''
        if mode in ('probe','nextbank'):
            # At the old full-batch boundary, an E8 can release the existing
            # producer while these confirmed OBJ records remain buffered.
            tail=''' if(p->count==15 && !p->obj_start){
  uint8_t flags;
  if(!poll(p,&flags,NES_PLAN215_FLUSH))return false;
  SECOND
 }
'''.replace('SECOND','if((flags&4) && !poll(p,&flags,NES_PLAN215_FLUSH))return false;' if mode=='nextbank' else '')
        if mode in ('mixed','mixedack'):
            tail=''' if(p->count==15 && p->obj_start && p->bytes-p->obj_start==112){
  const uint8_t *first=p->buffer+4+p->obj_start;
  if(first[11]!=first[3]+1)return true;
 }
'''
        if mode=='prefix':
            tail=''' if(p->count==15 && p->obj_start==7 && p->bytes==119 &&
    p->buffer[22]!=p->buffer[14]+1){
  uint8_t saved[4];memcpy(saved,p->buffer+11,4);
  p->count=1;p->bytes=7;
  if(!flush(p))return false;
  memcpy(p->buffer+11,saved,4);memmove(p->buffer+4,p->buffer+11,112);
  p->count=14;p->bytes=112;return true;
 }
'''
        s=s[:a]+tail+' if(p->count<15 || !p->obj_start)return true;\n'+s[b:]
    path.write_text(s,newline='\n')
    if mode=='pairidle':
        src=link/'src/nes_native_sink165.c'
        # Apply just the separately tested 922 OAM queue-opening change.
        base=(PREVIOUS/'oam/link/src'/src.name).read_text()
        delayed=(PREVIOUS/'idle/link/src'/src.name).read_text()
        assert '84u*512u' in delayed and '84u*512u' not in base
        assert src.read_text()==(PREVIOUS/'rows/link/src'/src.name).read_text()
        src.write_text(delayed,newline='\n')


def replay(temp,mode,phase,cold):
    def monitor(source,scene):
        return once(trace(source,scene),'pb(0)==7 and pw(8)==908','pb(0)==7 and pw(8)==909')
    with patch.object(peer,'PeerLink',LeadingRecord),patch.object(peer,'CLIENT',client('first')),patch.object(peer,'monitor',monitor):
        peer.compare(temp,phase,cold,True,edition=915,work_arm=WORK/mode,run_id='923'+mode)


def obj_stops(temp,mode,*,tag=None,destination=None,lengths=(32,352),output_prefix="obj-stop"):
    from guard_nes_output852 import run
    folder=temp/f'nes-tile821-obj-jointmirror-p1-{tag or "923"+mode}-warm-pair'
    outcomes={}
    for length in lengths:
        def adapt(lua,labels):
            lua=once(lua,'if not injected852 then','if false and not injected852 then')
            lua=once(lua,'local i=a-0x400800;',f'''local i=a-0x400800;
 if pw(8)==909 and pb(1)==1 and #tile=={length} and i=={length-1} then
  injected852=true;stop852=true end;''')
            original="if pb(0)==7 then assert(lastStatus==0 and reads==#tile,'early bulk ACK')end"
            lua=once(lua,original,f'if injected852 then assert(lastStatus==228 and reads=={length}) else {original} end')
            lua=once(lua,'consumed[#consumed+1]=',"assert(not injected852,'returned canceled OBJ');consumed[#consumed+1]=")
            return once(lua,'  assert(captured==commits)','  assert(injected852);assert(captured==commits)')
        outcomes[length]=run(temp,folder,'stop',column_client=client('first'),output_name=f'{output_prefix}-{length}',
                             select_packet=lambda b,g:g==909 and b[:2]==bytes((7,1)) and int.from_bytes(b[14:16],'little')==length,
                             adapt_lua=adapt)
    (destination or WORK/f'{mode}-stops.json').write_text(json.dumps(outcomes,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','proof','guards','stops'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,nargs='?')
    p.add_argument('--cold',action='store_true')
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        replay(a.temp,a.mode,a.phase,a.cold)
    elif a.action=='proof':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',WORK/a.mode,915)
    elif a.action=='stops':
        obj_stops(a.temp,a.mode)
    else:
        guards(a.temp,'first',tag='923'+a.mode,destination=WORK/(a.mode+'-guards.json'))
